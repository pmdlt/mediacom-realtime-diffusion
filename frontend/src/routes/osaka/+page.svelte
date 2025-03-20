<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import type { Fields, PipelineInfo } from '$lib/types';
  import { PipelineMode } from '$lib/types';
  import ImagePlayer from '$lib/components/ImagePlayer.svelte';
  import VideoInput from '$lib/components/VideoInput.svelte';
  import PipelineOptions from '$lib/components/PipelineOptions.svelte';
  import Spinner from '$lib/icons/spinner.svelte';
  import Warning from '$lib/components/Warning.svelte';
  import { lcmLiveStatus, lcmLiveActions, LCMLiveStatus } from '$lib/lcmLive';
  import { mediaStreamActions, onFrameChangeStore } from '$lib/mediaStream';
  import { getPipelineValues, deboucedPipelineValues } from '$lib/store';

  let pipelineParams: Fields;
  let pipelineInfo: PipelineInfo;
  let pageContent: string;
  let isImageMode: boolean = false;
  let maxQueueSize: number = 0;
  let currentQueueSize: number = 0;
  let queueCheckerRunning: boolean = false;
  let warningMessage: string = '';

  onMount(() => {
    getSettings().then(() => startLcmLive());
  });

  onDestroy(() => {
    stopLcmLive();
  });

  async function getSettings() {
    const settings = await fetch('/api/settings').then((r) => r.json());
    pipelineParams = settings.input_params.properties;
    pipelineInfo = settings.info.properties;
    isImageMode = pipelineInfo.input_mode.default === PipelineMode.IMAGE;
    maxQueueSize = settings.max_queue_size;
    pageContent = settings.page_content;
    console.log(pipelineParams);
    toggleQueueChecker(true);
  }

  function toggleQueueChecker(start: boolean) {
    queueCheckerRunning = start && maxQueueSize > 0;
    if (start) {
      getQueueSize();
    }
  }

  async function getQueueSize() {
    if (!queueCheckerRunning) {
      return;
    }
    const data = await fetch('/api/queue').then((r) => r.json());
    currentQueueSize = data.queue_size;
    setTimeout(getQueueSize, 10000);
  }

  function getStreamData() {
    if (isImageMode) {
      return [getPipelineValues(), $onFrameChangeStore?.blob];
    } else {
      return [$deboucedPipelineValues];
    }
  }

  async function startLcmLive() {
    try {
      if (isImageMode) {
        await mediaStreamActions.enumerateDevices();
        await mediaStreamActions.start();
      }
      await lcmLiveActions.start(getStreamData);
      toggleQueueChecker(false);
    } catch (e) {
      warningMessage = e instanceof Error ? e.message : '';
      toggleQueueChecker(true);
    }
  }

  function stopLcmLive() {
    if (isImageMode) {
      mediaStreamActions.stop();
    }
    lcmLiveActions.stop();
    toggleQueueChecker(true);
  }
</script>

<svelte:head>
  <script src="/iframeResizer.js"></script>
</svelte:head>

<main class="container mx-auto flex max-w-5xl flex-col gap-3 px-4 py-4">
  <Warning bind:message={warningMessage}></Warning>
  <article class="text-center">
    <h1 class="text-3xl font-bold">The New Possibilities of Deepfakes Enabled by AI</h1>
    <h3 class="text-xl font-bold">
      Thanks to "diffusion models" (AI systems that generate images), it is now possible to create
      anything on the fly from a video using a simple prompt.
    </h3>
    <p class="text-sm">
      In this case, we instructed the AI to transform the environment as if you were a little girl
      in the Swiss mountains. All that's left for you to do is start yodeling!
    </p>
  </article>
  {#if pipelineParams}
    <article class="my-3 grid grid-cols-1 gap-3 sm:grid-cols-4">
      {#if isImageMode}
        <div class="col-span-2 sm:col-start-1">
          <VideoInput
            width={Number(pipelineParams.width.default)}
            height={Number(pipelineParams.height.default)}
          ></VideoInput>
        </div>
      {/if}
      <div class={isImageMode ? 'col-span-2 sm:col-start-3' : 'col-span-4'}>
        <ImagePlayer />
      </div>
    </article>
  {:else}
    <div class="flex items-center justify-center gap-3 py-48 text-2xl">
      <Spinner classList={'animate-spin opacity-50'}></Spinner>
      <p>Loading...</p>
    </div>
  {/if}
  <!-- EPFL logo at the bottom right of the page -->
  <!-- <img src="/epfl-logo.svg" alt="EPFL Logo" class="epfl-logo"> -->
</main>

<style lang="postcss">
  :global(html) {
    @apply bg-black text-white;
  }

  :global(body) {
    @apply bg-black text-white;
  }

  :global(main) {
    @apply bg-black text-white;
  }

  .epfl-logo {
    position: fixed;
    bottom: 10px;
    right: 10px;
    width: 300px; /* Adjust the size as needed */
    opacity: 0.8; /* Adjust the opacity as needed */
  }
</style>
