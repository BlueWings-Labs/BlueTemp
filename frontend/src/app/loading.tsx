import LoadingIndicator from "./components/LoadingIndicator";
import ThemedPage from "./components/ThemedPage";

export default function Loading() {
  return (
    <ThemedPage theme="app">
      <LoadingIndicator layout="fullscreen" size="xl" />
    </ThemedPage>
  );
}
