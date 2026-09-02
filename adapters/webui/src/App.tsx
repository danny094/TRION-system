import { DesktopShell } from '@/app/shell/DesktopShell'
import { AuthGate } from '@/features/auth/AuthGate'

function App() {
  return (
    <AuthGate>
      <DesktopShell />
    </AuthGate>
  )
}

export default App
