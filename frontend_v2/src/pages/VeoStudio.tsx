import React, { useEffect, useRef, useState } from 'react';
import ApiKeyDialog from '../components/veo/ApiKeyDialog';
import LoadingIndicator from '../components/veo/LoadingIndicator';
import ProjectSetupForm from '../components/veo/VeoProjectForm';
import ShotBookDisplay from '../components/veo/ShotBookDisplay';
import { StopCircleIcon, KeyIcon, CheckCircle2Icon, UploadCloudIcon } from '../components/veo/icons';
import {
  generateKeyframeImage,
  generateKeyframePromptText,
  generateProjectName,
  generateShotList,
  generateVeoJson,
  generateSceneNames,
  extractAssetsFromScript,
  generateProjectSummary,
  analyzeVisualIdentity,
  embedArtifactData,
  refineVeoJson
} from '../services/geminiService';
import {
  generateVeoVideo,
  getVeoTaskDetails
} from '../services/veoService';
import {
  uploadToGCS,
  getAccessTokenFromServiceAccount,
  fetchSecretKey,
  listProjectsFromVault,
  vaultAssetToLibrary,
  legacyProjectInstaller,
  updateWorldRegistry,
  proxyVeoToVault,
  DEFAULT_BUCKET
} from '../services/cloudService';
import {
  AppState,
  IngredientImage,
  LogType,
  Shot,
  ShotBook,
  ShotStatus,
  ProjectAsset,
  VeoStatus,
  VeoShotWrapper
} from '../types';

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));
const API_CALL_DELAY_MS = 1200;
const ownerEmail = 'director@aether.studio';

const safeB64Encode = (str: string) => {
  return btoa(encodeURIComponent(str).replace(/%([0-9A-F]{2})/g, (match, p1) => {
    return String.fromCharCode(parseInt(p1, 16));
  }));
};

const fileToBase64 = (file: File): Promise<string> =>
  new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => resolve((reader.result as string).split(',')[1]);
    reader.onerror = (error) => reject(error);
  });

const App: React.FC = () => {
  const [appState, setAppState] = useState<AppState>(AppState.IDLE);
  const [shotBook, setShotBook] = useState<ShotBook | null>(null);
  const [projectName, setProjectName] = useState<string | null>(null);
  const [veoApiKey, setVeoApiKey] = useState<string>('');
  const [gcpToken, setGcpToken] = useState<string>('');
  const [vaultProjects, setVaultProjects] = useState<string[]>([]);
  const [assets, setAssets] = useState<ProjectAsset[]>([]);
  const [isAnalyzingAssets, setIsAnalyzingAssets] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [script, setScript] = useState('');
  const stopGenerationRef = useRef(false);
  const [logEntries, setLogEntries] = useState<{ timestamp: string; message: string; type: LogType }[]>([]);
  const [showApiKeyDialog, setShowApiKeyDialog] = useState(false);
  const [serviceAccountKey, setServiceAccountKey] = useState<any>(null);

  useEffect(() => {
    const checkApiKey = async () => {
      const aistudio = (window as any).aistudio;
      if (typeof aistudio?.hasSelectedApiKey === 'function') {
        const hasKey = await aistudio.hasSelectedApiKey();
        if (!hasKey) setShowApiKeyDialog(true);
      }
    };
    checkApiKey();
  }, []);

  useEffect(() => {
    if (gcpToken && !serviceAccountKey && !veoApiKey) {
      handleFetchVeoSecret();
    }
    if (gcpToken) {
      listProjectsFromVault(gcpToken).then(setVaultProjects).catch(console.error);
    }
  }, [gcpToken]);

  useEffect(() => {
    if (!serviceAccountKey) return;
    let timeoutId: number;
    const refresh = async () => {
      try {
        const authResult = await getAccessTokenFromServiceAccount(serviceAccountKey);
        setGcpToken(authResult.access_token);
        const refreshInMs = (authResult.expires_in - 300) * 1000;
        timeoutId = window.setTimeout(refresh, Math.max(refreshInMs, 60000));
      } catch (e) {
        addLogEntry(`Auth Agent Critical Failure: ${(e as Error).message}`, LogType.ERROR);
      }
    };
    refresh();
    return () => window.clearTimeout(timeoutId);
  }, [serviceAccountKey]);

  const addLogEntry = (message: string, type: LogType = LogType.INFO) => {
    setLogEntries((prev) => [...prev, { timestamp: new Date().toLocaleTimeString(), message, type }]);
  };

  const findAssetIdsForShot = (shot: Shot, veoJson: VeoShotWrapper | undefined, currentAssets: ProjectAsset[]) => {
    const ids = new Set<string>();
    const pitch = shot.pitch.toLowerCase();
    currentAssets.forEach(asset => {
      const assetName = asset.name.toLowerCase();
      if (assetName.length > 2 && pitch.includes(assetName)) ids.add(asset.id);
    });
    if (veoJson?.veo_shot) {
      const charName = veoJson.veo_shot.character.name.toLowerCase();
      const sceneContext = veoJson.veo_shot.scene.context.toLowerCase();
      currentAssets.forEach(asset => {
        const assetName = asset.name.toLowerCase();
        if (assetName.length > 2) {
          if (charName.includes(assetName) || assetName.includes(charName)) ids.add(asset.id);
          if (sceneContext.includes(assetName) || assetName.includes(sceneContext)) ids.add(asset.id);
        }
      });
    }
    return Array.from(ids);
  };

  const handleUpdateAssetImage = async (id: string, file: File) => {
    try {
      const base64 = await fileToBase64(file);
      const asset = assets.find(a => a.id === id);
      if (!asset) return;
      const visionMeta = await analyzeVisualIdentity(base64, file.type);
      const semanticFingerprint = await embedArtifactData(`${asset.name}: ${visionMeta.detailed_description}`);
      if (gcpToken) {
        await vaultAssetToLibrary(asset.type, asset.name, base64, { ...visionMeta, semantic_fingerprint: semanticFingerprint }, gcpToken);
      }
      setAssets(prev => prev.map(a => a.id === id ? { ...a, image: { base64, mimeType: file.type }, description: visionMeta.detailed_description } : a));
      addLogEntry(`Visual Lock applied to ${asset.name}.`, LogType.SUCCESS);
    } catch (e) {
      addLogEntry(`Vision Agent Failed: ${(e as Error).message}`, LogType.ERROR);
    }
  };

  const handleRefineShot = async (shotId: string, feedback: string) => {
    const shot = shotBook?.find(s => s.id === shotId);
    if (!shot || !shot.veoJson) return;
    setIsProcessing(true);
    addLogEntry(`Director Feedback received for unit ${shotId}. Re-authoring breakdown...`, LogType.STEP);
    try {
      const refinedData = await refineVeoJson(shot.veoJson, feedback, script);
      setShotBook(prev => prev?.map(s => s.id === shotId ? { ...s, veoJson: refinedData.result, status: ShotStatus.NEEDS_REVIEW } : s) || null);
      addLogEntry(`Unit ${shotId} breakdown updated.`, LogType.SUCCESS);
    } catch (e) {
      addLogEntry(`Refinement Agent Failure: ${(e as Error).message}`, LogType.ERROR);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleInstallLegacyProject = async (slug: string) => {
    if (!gcpToken) return;
    setAppState(AppState.LOADING);
    try {
      const state = await legacyProjectInstaller(slug, gcpToken);
      setShotBook(state.shotBook);
      setProjectName(state.projectName);
      setAssets(state.assets || []);
      setAppState(AppState.SUCCESS);
    } catch (e) {
      setAppState(AppState.IDLE);
      addLogEntry(`Installation failed: ${(e as Error).message}`, LogType.ERROR);
    }
  };

  const handleLoadProject = (jsonString: string) => {
    try {
      const state = JSON.parse(jsonString);
      if (state.shotBook && state.projectName) {
        setShotBook(state.shotBook);
        setProjectName(state.projectName);
        setAssets(state.assets || []);
        setAppState(AppState.SUCCESS);
      }
    } catch (e) {
      addLogEntry(`Failed to parse local project: ${(e as Error).message}`, LogType.ERROR);
    }
  };

  const handleArchiveExternalProject = async (jsonString: string) => {
    if (!gcpToken) return;
    setIsProcessing(true);
    addLogEntry("Vault: Ingesting external project to cloud...", LogType.STEP);
    try {
      const state = JSON.parse(jsonString);
      const pName = state.projectName || `ext-archive-${Date.now()}`;
      const summary = await generateProjectSummary(pName, state.assets || [], state.shotBook || []);
      await uploadToGCS(`projects/${pName}/state.json`, safeB64Encode(jsonString), 'application/json', gcpToken);
      await updateWorldRegistry(gcpToken, { projects: [pName], summaries: { [pName]: summary }, last_sync: new Date().toISOString() });
      listProjectsFromVault(gcpToken).then(setVaultProjects).catch(console.error);
      addLogEntry(`Vault: ${pName} ingested successfully.`, LogType.SUCCESS);
    } catch (e) {
      addLogEntry(`Ingest Failed: ${(e as Error).message}`, LogType.ERROR);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleCloudSync = async () => {
    if (!gcpToken || !projectName || !shotBook) {
      addLogEntry("Vault: Cannot sync. Missing token or project state.", LogType.ERROR);
      return;
    }
    setIsProcessing(true);
    addLogEntry(`Vault: Synchronizing "${projectName}" to ${DEFAULT_BUCKET}...`, LogType.STEP);
    try {
      const state = { projectName, shotBook, assets, exportedAt: new Date().toISOString() };
      const summary = await generateProjectSummary(projectName, assets, shotBook);
      await uploadToGCS(`projects/${projectName}/state.json`, safeB64Encode(JSON.stringify(state)), 'application/json', gcpToken);
      const manifestMd = `# Production Manifest: ${projectName}\n\n` +
        `**Director:** ${ownerEmail}\n` +
        `**Timestamp:** ${new Date().toLocaleString()}\n\n` +
        `## Production Statistics\n` +
        `- Total Assets: ${assets.length}\n` +
        `- Total Shots: ${shotBook.length}\n` +
        `- Videos Produced: ${shotBook.filter(s => s.veoVideoUrl).length}\n\n` +
        `*Produced via Aether Studio World Agent.*`;
      await uploadToGCS(`projects/${projectName}/README_VAULT.md`, safeB64Encode(manifestMd), 'text/markdown', gcpToken);
      await updateWorldRegistry(gcpToken, { projects: [projectName], summaries: { [projectName]: summary }, last_sync: new Date().toISOString() });
      addLogEntry(`Vault Sync Successful. Manifests published to GCS.`, LogType.SUCCESS);
    } catch (e) {
      addLogEntry(`Vault Sync Failed: ${(e as Error).message}`, LogType.ERROR);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleAnalyzeScriptForAssets = async (scriptInput: string) => {
    if (!scriptInput.trim()) return;
    setScript(scriptInput);
    setIsAnalyzingAssets(true);
    addLogEntry(`Vision Agent: Scouting characters and set pieces...`, LogType.STEP);
    try {
      const { result } = await extractAssetsFromScript(scriptInput);
      setAssets(result);
      addLogEntry(`Vision Agent: Found ${result.length} artifacts. Mapping to library...`, LogType.SUCCESS);
    } catch (e) {
      addLogEntry(`Agent Failure: ${(e as Error).message}`, LogType.ERROR);
    } finally {
      setIsAnalyzingAssets(false);
    }
  };

  const performKeyframeGeneration = async (shotsArray: Shot[], index: number) => {
    const shot = shotsArray[index];
    if (!shot?.veoJson?.veo_shot) return;
    try {
      shot.status = ShotStatus.GENERATING_IMAGE;
      const promptData = await generateKeyframePromptText(shot.veoJson.veo_shot);
      const libIngredients = shot.selectedAssetIds.map(id => assets.find(a => a.id === id)?.image).filter(Boolean) as IngredientImage[];
      const adHocIngredients = shot.adHocAssets || [];
      const allIngredients = [...libIngredients, ...adHocIngredients];
      const aspectRatio = shot.veoJson?.veo_shot?.scene?.aspect_ratio || "16:9";
      const imageData = await generateKeyframeImage(promptData.result, allIngredients, aspectRatio);
      let cloudRef = undefined;
      if (gcpToken && projectName) {
        cloudRef = await uploadToGCS(`projects/${projectName}/units/${shot.id}/still.png`, imageData.result, 'image/png', gcpToken);
      }
      shot.keyframeImage = imageData.result;
      shot.veoReferenceUrl = cloudRef;
      shot.status = ShotStatus.NEEDS_REVIEW;
    } catch (err) {
      addLogEntry(`Imaging Agent Failure for ${shot.id}: ${(err as Error).message}`, LogType.ERROR);
      shot.status = ShotStatus.GENERATION_FAILED;
    }
  };

  const handleGenerate = async (scriptInput: string, createKeyframes: boolean) => {
    setScript(scriptInput);
    stopGenerationRef.current = false;
    setIsProcessing(true);
    setAppState(AppState.LOADING);
    setLogEntries([]);
    try {
      const nameData = await generateProjectName(scriptInput);
      setProjectName(nameData.result);
      addLogEntry(`Director: Initializing Production "${nameData.result}"`, LogType.STEP);
      const shotListData = await generateShotList(scriptInput);
      const initialShots: Shot[] = shotListData.result.map((s: any) => ({
        id: s.shot_id, status: ShotStatus.PENDING_JSON, pitch: s.pitch, selectedAssetIds: []
      }));
      setShotBook(initialShots);
      const sceneNamesData = await generateSceneNames(shotListData.result, scriptInput);
      const sceneMap = sceneNamesData.result.names;

      let finalShots = [...initialShots];
      for (let i = 0; i < finalShots.length; i++) {
        if (stopGenerationRef.current) break;
        const shot = finalShots[i];
        const sceneId = shot.id.split('_')[0];
        shot.sceneName = sceneMap.get(sceneId) || 'Untitled Scene';

        // Dynamic Context Injection
        const mappedAssets = assets.filter(a => shot.pitch.toLowerCase().includes(a.name.toLowerCase()));
        const assetContext = mappedAssets.map(a => `${a.name}: ${a.description}`).join('\n');

        try {
          const jsonData = await generateVeoJson(shot.pitch, shot.id, scriptInput, assetContext);
          finalShots[i].veoJson = jsonData.result;
          finalShots[i].selectedAssetIds = findAssetIdsForShot(shot, jsonData.result, assets);
          finalShots[i].status = ShotStatus.NEEDS_REVIEW;
        } catch (jsonErr) {
          addLogEntry(`Breakdown Failure for ${shot.id}: Truncated response.`, LogType.ERROR);
          continue;
        }
        if (createKeyframes && finalShots[i].veoJson?.veo_shot && finalShots[i].veoJson?.unit_type !== 'extend') {
          await performKeyframeGeneration(finalShots, i);
        }
        setShotBook([...finalShots]);
        await delay(API_CALL_DELAY_MS);
      }
      setAppState(AppState.SUCCESS);
    } catch (e) { setAppState(AppState.ERROR); } finally { setIsProcessing(false); }
  };

  const handleGenerateSpecificKeyframe = async (shotId: string) => {
    if (!shotBook) return;
    const index = shotBook.findIndex(s => s.id === shotId);
    if (index === -1) return;
    setIsProcessing(true);
    addLogEntry(`Imaging Agent: Manually developing unit ${shotId}...`, LogType.STEP);
    const updatedShots = [...shotBook];
    updatedShots[index].selectedAssetIds = findAssetIdsForShot(updatedShots[index], updatedShots[index].veoJson, assets);
    await performKeyframeGeneration(updatedShots, index);
    setShotBook(updatedShots);
    setIsProcessing(false);
  };

  const handleGenerateAllMissingKeyframes = async () => {
    if (!shotBook) return;
    setIsProcessing(true);
    stopGenerationRef.current = false;
    addLogEntry(`Imaging Agent: Initializing bulk development sequence...`, LogType.STEP);
    const updatedShots = [...shotBook];
    for (let i = 0; i < updatedShots.length; i++) {
      if (stopGenerationRef.current) break;
      const s = updatedShots[i];
      if (!s.keyframeImage && s.veoJson?.veo_shot && s.veoJson?.unit_type !== 'extend') {
        updatedShots[i].selectedAssetIds = findAssetIdsForShot(updatedShots[i], updatedShots[i].veoJson, assets);
        await performKeyframeGeneration(updatedShots, i);
        setShotBook([...updatedShots]);
        await delay(API_CALL_DELAY_MS);
      }
    }
    addLogEntry(`Development sequence complete.`, LogType.SUCCESS);
    setIsProcessing(false);
  };

  const handleGenerateVideo = async (shotId: string, useKeyframe: boolean) => {
    if (!veoApiKey) {
      addLogEntry("Production Aborted: No Kie API Key provided.", LogType.ERROR);
      return;
    }
    const shot = shotBook?.find(s => s.id === shotId);
    if (!shot || !shot.veoJson?.veo_shot) return;
    addLogEntry(`Production Agent: Enqueuing video task for ${shotId}...`, LogType.STEP);
    try {
      const vShot = shot.veoJson.veo_shot;
      const reqPrompt = `${vShot.scene.context} ${vShot.character.behavior} ${vShot.camera.shot_call}`;
      const ingredients = useKeyframe && shot.veoReferenceUrl ? [shot.veoReferenceUrl] : [];
      const response = await generateVeoVideo(veoApiKey, {
        prompt: reqPrompt, model: 'veo3_fast', aspectRatio: vShot.scene.aspect_ratio as any || '16:9', imageUrls: ingredients
      });
      const taskId = response.data.taskId;
      setShotBook(prev => prev?.map(s => s.id === shotId ? { ...s, veoStatus: VeoStatus.QUEUED } : s) || null);
      pollVeoTask(shotId, taskId);
    } catch (e) { addLogEntry(`Production Failure: ${(e as Error).message}`, LogType.ERROR); }
  };

  const pollVeoTask = async (shotId: string, taskId: string) => {
    let completed = false;
    while (!completed) {
      await delay(5000);
      try {
        const info = await getVeoTaskDetails(veoApiKey, taskId);
        if (info.data.successFlag === 1 && info.data.response?.resultUrls?.[0]) {
          const resultUrl = info.data.response.resultUrls[0];
          addLogEntry(`Production Agent: Task ${shotId} completed. Proxying to Vault...`, LogType.SUCCESS);
          let vaultUrl = resultUrl;
          if (gcpToken && projectName) vaultUrl = await proxyVeoToVault(resultUrl, projectName, shotId, gcpToken);
          setShotBook(prev => prev?.map(s => s.id === shotId ? { ...s, veoStatus: VeoStatus.COMPLETED, veoVideoUrl: vaultUrl } : s) || null);
          completed = true;
        } else if (info.data.successFlag === 2 || info.data.successFlag === 3) {
          setShotBook(prev => prev?.map(s => s.id === shotId ? { ...s, veoStatus: VeoStatus.FAILED } : s) || null);
          completed = true;
        } else if (info.data.successFlag === 0) {
          setShotBook(prev => prev?.map(s => s.id === shotId ? { ...s, veoStatus: VeoStatus.GENERATING } : s) || null);
        }
      } catch (e) { console.error("Polling error:", e); }
    }
  };

  const handleUploadAdHocAsset = async (shotId: string, file: File) => {
    try {
      const base64 = await fileToBase64(file);
      setShotBook(prev => prev?.map(s => s.id === shotId ? {
        ...s,
        adHocAssets: [...(s.adHocAssets || []), { base64, mimeType: file.type }]
      } : s) || null);
      addLogEntry(`Ad-hoc asset added to unit ${shotId}.`, LogType.INFO);
    } catch (e) {
      addLogEntry(`Asset upload failed: ${(e as Error).message}`, LogType.ERROR);
    }
  };

  const handleRemoveAdHocAsset = (shotId: string, index: number) => {
    setShotBook(prev => prev?.map(s => s.id === shotId ? {
      ...s,
      adHocAssets: s.adHocAssets?.filter((_, i) => i !== index)
    } : s) || null);
    addLogEntry(`Ad-hoc asset removed from unit ${shotId}.`, LogType.INFO);
  };

  const handleSaveProject = () => {
    if (!shotBook || !projectName) return;
    const state = { projectName, shotBook, assets, exportedAt: new Date().toISOString() };
    const blob = new Blob([JSON.stringify(state, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${projectName}_workspace.json`;
    link.click();
    addLogEntry("Project Workspace Snapshot saved to local disk.", LogType.SUCCESS);
  };

  const handleDownloadKeyframesZip = async () => {
    if (!shotBook || !projectName) return;
    setIsProcessing(true);
    addLogEntry("Packaging Agent: Zipping keyframe still set...", LogType.STEP);
    try {
      const zip = new (window as any).JSZip();
      shotBook.forEach(shot => {
        if (shot.keyframeImage) {
          zip.file(`${shot.id}.png`, shot.keyframeImage, { base64: true });
        }
      });
      const content = await zip.generateAsync({ type: "blob" });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(content);
      link.download = `${projectName}_keyframes.zip`;
      link.click();
    } catch (e) { addLogEntry("Keyframe zip failed.", LogType.ERROR); }
    finally { setIsProcessing(false); }
  };

  const handleExportPackage = async () => {
    if (!shotBook || !projectName) return;
    setIsProcessing(true);
    addLogEntry("Packaging Agent: Constructing Local Production Bundle (Pulling from Cloud)...", LogType.STEP);
    try {
      const zip = new (window as any).JSZip();
      const state = { projectName, shotBook, assets, exportedAt: new Date().toISOString() };
      zip.file("state.json", JSON.stringify(state, null, 2));
      const assetFolder = zip.folder("Assets");
      for (const asset of assets) {
        if (asset.image) {
          const folder = assetFolder.folder(asset.type);
          folder.file(`${asset.name.replace(/\s+/g, '_')}.png`, asset.image.base64, { base64: true });
        }
      }
      const productionFolder = zip.folder("Production");
      for (const shot of shotBook) {
        const shotFolder = productionFolder.folder(shot.id);
        if (shot.veoJson) shotFolder.file("prompt.json", JSON.stringify(shot.veoJson, null, 2));
        if (shot.keyframeImage) shotFolder.file("still.png", shot.keyframeImage, { base64: true });
        if (shot.veoVideoUrl && gcpToken) {
          try {
            addLogEntry(`Packaging: Pulling cloud clip for ${shot.id}...`, LogType.INFO);
            const response = await fetch(shot.veoVideoUrl, { headers: { 'Authorization': `Bearer ${gcpToken}` } });
            if (response.ok) {
              const blob = await response.blob();
              shotFolder.file("clip.mp4", blob);
            }
          } catch (e) { console.error("Failed to pull clip for package:", e); }
        }
      }
      const content = await zip.generateAsync({ type: "blob" });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(content);
      link.download = `${projectName}_local_package.zip`;
      link.click();
      addLogEntry("Local Production Bundle exported.", LogType.SUCCESS);
    } catch (e) { addLogEntry(`Local Package error: ${(e as Error).message}`, LogType.ERROR); }
    finally { setIsProcessing(false); }
  };

  const handleFetchVeoSecret = async () => {
    try {
      const secretContent = await fetchSecretKey(gcpToken);
      try {
        const saJson = JSON.parse(secretContent);
        if (saJson.type === 'service_account') setServiceAccountKey(saJson);
        else setVeoApiKey(secretContent);
        addLogEntry("Vault: Decrypted Kie session credentials.", LogType.SUCCESS);
      } catch (e) {
        setVeoApiKey(secretContent);
        addLogEntry("Vault: Decrypted Kie static key.", LogType.SUCCESS);
      }
    } catch (e) { addLogEntry(`Vault Access Denied.`, LogType.ERROR); }
  };

  return (
    <div className="min-h-screen font-sans text-gray-100 bg-[#050505]">
      {showApiKeyDialog && <ApiKeyDialog onContinue={() => setShowApiKeyDialog(false)} />}
      {appState === AppState.LOADING && (
        <div className="fixed inset-0 bg-black/95 flex items-center justify-center z-50 backdrop-blur-2xl">
          <LoadingIndicator />
          <div className="absolute bottom-10"><button onClick={() => { stopGenerationRef.current = true; setIsProcessing(false); }} className="px-8 py-3 bg-red-950/50 border border-red-500/50 text-red-500 rounded-2xl flex items-center gap-2 hover:bg-red-900/50 transition-all font-black uppercase italic tracking-tighter"><StopCircleIcon className="w-5 h-5" /> Terminate Pipeline</button></div>
        </div>
      )}
      <main className="flex flex-col items-center p-4 md:p-8 min-h-screen max-w-[1920px] mx-auto">
        {appState === AppState.IDLE && (
          <div className="flex flex-col items-center w-full max-w-5xl animate-in fade-in zoom-in-95 duration-1000">
            <div className="mb-16 text-center">
              <div className="flex items-center justify-center gap-4 mb-6">
                <div className="w-24 h-1 bg-gradient-to-r from-transparent to-indigo-500 rounded-full"></div>
                <h1 className="text-7xl md:text-9xl font-black text-transparent bg-clip-text bg-gradient-to-b from-white via-indigo-400 to-purple-600 tracking-tighter italic">AETHER</h1>
                <div className="w-24 h-1 bg-gradient-to-l from-transparent to-indigo-500 rounded-full"></div>
              </div>
              <p className="text-2xl text-gray-500 max-w-3xl mx-auto font-light leading-tight">Connected World Agent for <strong>{ownerEmail}</strong>. Orchestrating semantic narrative artifacts via <strong>{DEFAULT_BUCKET}</strong>.</p>
              <div className="mt-8 flex justify-center items-center gap-4">
                <input id="gcp-token-input" type="hidden" value={gcpToken} onChange={(e) => setGcpToken(e.target.value)} />
                <button id="vault-unlock-btn" className="hidden" onClick={handleFetchVeoSecret}></button>
                <div className="flex items-center gap-4 bg-gray-900/40 border border-gray-800 rounded-2xl px-6 py-3">
                  <div className={`p-2 rounded-lg ${gcpToken ? 'bg-indigo-600/20 text-indigo-400' : 'bg-gray-800 text-gray-600'}`}>
                    <KeyIcon className="w-5 h-5" />
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[10px] font-black uppercase tracking-widest text-gray-500">Aether Vault Status</span>
                    <span className={`text-xs font-bold ${gcpToken ? 'text-indigo-400' : 'text-gray-600'}`}>
                      {gcpToken ? 'Encrypted Connection Active' : 'Awaiting Extension Injection...'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
            <ProjectSetupForm onGenerate={handleGenerate} isGenerating={false} onLoadProject={handleLoadProject} onArchiveProject={handleArchiveExternalProject} assets={assets} onAnalyzeScriptForAssets={handleAnalyzeScriptForAssets} isAnalyzingAssets={isAnalyzingAssets} onAddAsset={(a) => setAssets(prev => [...prev, a])} onRemoveAsset={(id) => setAssets(prev => prev.filter(a => a.id !== id))} onUpdateAssetImage={handleUpdateAssetImage} onAddLogEntry={addLogEntry} />
          </div>
        )}
        {appState !== AppState.IDLE && shotBook && (
          <ShotBookDisplay
            shotBook={shotBook} logEntries={logEntries} projectName={projectName} scenePlans={[]} apiCallSummary={{ pro: 0, flash: 0, image: 0, proTokens: { input: 0, output: 0 }, flashTokens: { input: 0, output: 0 } }} appVersion="0.2.0"
            onNewProject={() => setAppState(AppState.IDLE)} onUpdateShot={(s) => setShotBook(prev => prev?.map(sh => sh.id === s.id ? s : sh) || null)}
            onGenerateSpecificKeyframe={handleGenerateSpecificKeyframe} onRefineShot={handleRefineShot} allAssets={assets} onToggleAssetForShot={(shotId, assetId) => setShotBook(prev => prev?.map(s => s.id === shotId ? { ...s, selectedAssetIds: s.selectedAssetIds.includes(assetId) ? s.selectedAssetIds.filter(id => id !== assetId) : [...s.selectedAssetIds, assetId] } : s) || null)}
            allIngredientImages={[]} onUpdateShotIngredients={() => { }} onExportAllJsons={() => { }} onExportHtmlReport={() => { }} onSaveProject={handleSaveProject} onDownloadKeyframesZip={handleDownloadKeyframesZip} onExportPackage={handleExportPackage} onShowStorageInfo={() => { }} isProcessing={isProcessing}
            onStopGeneration={() => { stopGenerationRef.current = true; }} veoApiKey={veoApiKey} onSetVeoApiKey={setVeoApiKey}
            onGenerateVideo={handleGenerateVideo}
            onExtendVeoVideo={() => { }}
            onUploadAdHocAsset={handleUploadAdHocAsset}
            onRemoveAdHocAsset={handleRemoveAdHocAsset}
            onApproveShot={(shotId, approved) => setShotBook(prev => prev?.map(s => s.id === shotId ? { ...s, isApproved: approved } : s) || null)}
            gcpToken={gcpToken} onSetGcpToken={setGcpToken} onFetchVeoSecret={handleFetchVeoSecret} onCloudSync={handleCloudSync} ownerEmail={ownerEmail} onGenerateAllKeyframes={handleGenerateAllMissingKeyframes}
          />
        )}
      </main>
    </div>
  );
};

export default App;
