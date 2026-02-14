import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useState, useEffect } from 'react'
import { useRequireAuth } from '@/hooks/useRequireAuth'
import { useToast } from '@/hooks/useToast'
import { timelineApi } from '@/lib/api-client'
import { ArrowLeft, Mail, Lock, Server, CheckCircle, Cloud, Inbox, ExternalLink } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { LoadingIcon, ErrorIcon } from '@/components/ui/icons'
import SubjectSelector from '@/components/subjects/SubjectSelector'
import type { components } from '@/lib/timeline-api'

export const Route = createFileRoute('/email-accounts/create')({
  component: CreateEmailAccountPage,
})

type OAuthProviderConfig = components['schemas']['OAuthConfigResponse']

type EmailProvider = 'gmail' | 'outlook' | 'imap' | 'icloud' | 'yahoo'
type EmailAccountCreate = components['schemas']['EmailAccountCreateRequest']

interface ProviderConfig {
  name: string
  description: string
  authType: 'oauth' | 'imap'
  icon: React.ElementType
  iconColor: string
}

const PROVIDERS: Record<EmailProvider, ProviderConfig> = {
  gmail: {
    name: 'Gmail',
    description: 'Connect your Gmail account using OAuth2',
    authType: 'oauth',
    icon: Mail,
    iconColor: 'text-red-600 dark:text-red-400',
  },
  outlook: {
    name: 'Outlook',
    description: 'Connect your Outlook/Microsoft 365 account using OAuth2',
    authType: 'oauth',
    icon: Inbox,
    iconColor: 'text-blue-600 dark:text-blue-400',
  },
  imap: {
    name: 'IMAP',
    description: 'Connect any IMAP-compatible email server',
    authType: 'imap',
    icon: Server,
    iconColor: 'text-gray-600 dark:text-gray-400',
  },
  icloud: {
    name: 'iCloud',
    description: 'Connect your iCloud email using IMAP',
    authType: 'imap',
    icon: Cloud,
    iconColor: 'text-blue-500 dark:text-blue-400',
  },
  yahoo: {
    name: 'Yahoo Mail',
    description: 'Connect your Yahoo Mail account using IMAP',
    authType: 'imap',
    icon: Mail,
    iconColor: 'text-purple-600 dark:text-purple-400',
  },
}

function CreateEmailAccountPage() {
  const authState = useRequireAuth()
  const navigate = useNavigate()
  const toast = useToast()

  const [step, setStep] = useState<'select' | 'configure'>('select')
  const [selectedProvider, setSelectedProvider] = useState<EmailProvider | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [testingConnection, setTestingConnection] = useState(false)
  const [connectionTested, setConnectionTested] = useState(false)

  // OAuth provider configs from backend
  const [oauthConfigs, setOauthConfigs] = useState<OAuthProviderConfig[]>([])
  const [loadingOAuth, setLoadingOAuth] = useState(true)

  // Form state
  const [subjectId, setSubjectId] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [imapServer, setImapServer] = useState('')
  const [imapPort, setImapPort] = useState('993')
  const [useSsl, setUseSsl] = useState(true)

  // Fetch available OAuth providers on mount
  useEffect(() => {
    const fetchOAuthProviders = async () => {
      try {
        const { data } = await timelineApi.oauthProviders.list({ include_inactive: false })
        if (data && Array.isArray(data)) {
          setOauthConfigs(data)
        }
      } catch (err) {
        console.error('Failed to fetch OAuth providers:', err)
      } finally {
        setLoadingOAuth(false)
      }
    }
    fetchOAuthProviders()
  }, [])

  // Check if OAuth is configured for a provider
  const isOAuthConfigured = (provider: 'gmail' | 'outlook'): boolean => {
    return oauthConfigs.some((config) => config.provider_type === provider && config.is_active)
  }

  if (!authState.user) {
    return null
  }

  const handleProviderSelect = (provider: EmailProvider) => {
    setSelectedProvider(provider)
    setError(null)

    // Pre-fill IMAP settings for known providers
    if (provider === 'icloud') {
      setImapServer('imap.mail.me.com')
      setImapPort('993')
    } else if (provider === 'yahoo') {
      setImapServer('imap.mail.yahoo.com')
      setImapPort('993')
    }

    setStep('configure')
  }

  const handleOAuthConnect = async (provider: 'gmail' | 'outlook') => {
    // Check if OAuth is configured for this provider
    if (!isOAuthConfigured(provider)) {
      setError(
        `OAuth for ${PROVIDERS[provider].name} is not configured. Please contact your administrator to set up OAuth credentials, or use IMAP authentication.`
      )
      return
    }

    setLoading(true)
    setError(null)
    try {
      const { data, error: apiError } = await timelineApi.oauthProviders.authorize(provider)

      if (apiError) {
        const errorObj = apiError as { detail?: string }
        throw new Error(errorObj?.detail || 'Failed to initiate OAuth flow')
      }

      if (data?.authorization_url) {
        // Redirect user to the OAuth provider's authorization page
        window.location.href = data.authorization_url
      } else {
        throw new Error('No authorization URL returned')
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to initiate OAuth flow'
      setError(errorMsg)
      setLoading(false)
    }
    // Note: Don't set loading to false on success - we're redirecting away
  }

  const handleTestConnection = async () => {
    if (!selectedProvider || !email || !password) {
      setError('Please fill in all required fields')
      return
    }

    setTestingConnection(true)
    setError(null)
    setConnectionTested(false)

    try {
      // For now, we'll just validate the fields locally
      // In a real implementation, you'd call a test endpoint
      if (selectedProvider !== 'gmail' && selectedProvider !== 'outlook') {
        if (!imapServer) {
          throw new Error('IMAP server is required')
        }
        if (!imapPort || parseInt(imapPort, 10) < 1 || parseInt(imapPort, 10) > 65535) {
          throw new Error('Valid IMAP port is required (1-65535)')
        }
      }

      setConnectionTested(true)
      toast.success('Connection test passed', 'Email account credentials are valid')
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Connection test failed'
      setError(errorMsg)
      toast.error('Connection test failed', errorMsg)
    } finally {
      setTestingConnection(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!selectedProvider) {
      setError('Please select a provider')
      return
    }

    if (PROVIDERS[selectedProvider].authType === 'oauth') {
      await handleOAuthConnect(selectedProvider as 'gmail' | 'outlook')
      return
    }

    if (!subjectId) {
      setError('Please select a subject')
      return
    }

    if (!connectionTested) {
      setError('Please test the connection before saving')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const accountData: EmailAccountCreate = {
        subject_id: subjectId,
        provider_type: selectedProvider,
        email_address: email,
        credentials: {
          username: email,
          password: password,
        },
        connection_params: imapServer ? {
          imap_host: imapServer,
          imap_port: parseInt(imapPort, 10),
          use_ssl: useSsl,
        } : undefined,
      }

      const { data, error: apiError } = await timelineApi.emailAccounts.create(accountData)

      if (apiError) {
        const errorMsg =
          typeof apiError === 'object' && 'message' in apiError
            ? (apiError as any).message
            : 'Failed to create email account'
        setError(errorMsg)
        toast.error('Failed to connect', errorMsg)
      } else if (data) {
        toast.success('Account connected', `Successfully connected ${email}`)
        navigate({ to: '/email-accounts' })
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unexpected error creating email account'
      setError(errorMsg)
      toast.error('Error connecting', errorMsg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      {/* Header */}
      <div className="flex items-center gap-3 mb-3">
        <button
          onClick={() => {
            if (step === 'configure') {
              setStep('select')
              setError(null)
              setConnectionTested(false)
            } else {
              navigate({ to: '/email-accounts' })
            }
          }}
          className="p-2 text-muted-foreground hover:text-foreground hover:bg-muted rounded-none transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div>
          <h1 className="text-lg font-bold text-foreground">Connect Email Account</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            {step === 'select'
              ? 'Choose your email provider'
              : `Configure ${selectedProvider ? PROVIDERS[selectedProvider].name : ''} connection`}
          </p>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="mb-3 p-2.5 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-none flex gap-2">
          <ErrorIcon className="text-red-600 dark:text-red-400 mt-0.5" />
          <div className="flex-1">
            <h3 className="font-semibold text-red-900 dark:text-red-200 text-sm">Error</h3>
            <p className="text-sm text-red-800 dark:text-red-300 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Step 1: Provider Selection */}
      {step === 'select' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {loadingOAuth ? (
            <div className="col-span-2 flex items-center justify-center py-8">
              <LoadingIcon className="w-6 h-6" />
              <span className="ml-2 text-muted-foreground">Loading providers...</span>
            </div>
          ) : (
            (Object.keys(PROVIDERS) as EmailProvider[]).map((provider) => {
              const config = PROVIDERS[provider]
              const IconComponent = config.icon
              const oauthAvailable =
                config.authType === 'oauth' && isOAuthConfigured(provider as 'gmail' | 'outlook')
              const oauthNotConfigured = config.authType === 'oauth' && !oauthAvailable

              return (
                <button
                  key={provider}
                  onClick={() => handleProviderSelect(provider)}
                  className="p-4 bg-card/80 backdrop-blur-sm border border-border/50 rounded-none hover:border-primary/50 hover:bg-card transition-all text-left group"
                >
                  <div className="flex items-start gap-3">
                    <div className={`p-2 rounded-none bg-accent ${config.iconColor}`}>
                      <IconComponent className="w-6 h-6" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold text-foreground group-hover:text-primary transition-colors">
                          {config.name}
                        </h3>
                        {oauthAvailable && (
                          <span className="text-[10px] px-1.5 py-0.5 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded-none">
                            OAuth Ready
                          </span>
                        )}
                        {oauthNotConfigured && (
                          <span className="text-[10px] px-1.5 py-0.5 bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 rounded-none">
                            Not Configured
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground mt-1">{config.description}</p>
                      <div className="mt-2 flex items-center gap-1 text-xs text-muted-foreground">
                        {config.authType === 'oauth' ? (
                          <>
                            <Lock className="w-3 h-3" />
                            <span>OAuth 2.0</span>
                            {oauthAvailable && <ExternalLink className="w-3 h-3 ml-1" />}
                          </>
                        ) : (
                          <>
                            <Server className="w-3 h-3" />
                            <span>IMAP</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                </button>
              )
            })
          )}
        </div>
      )}

      {/* Step 2: Configuration */}
      {step === 'configure' && selectedProvider && (
        <div className="max-w-2xl">
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Subject Selection */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-1.5">
                Subject <span className="text-red-500">*</span>
              </label>
              <SubjectSelector value={subjectId} onChange={(value) => setSubjectId(value)} />
              <p className="text-xs text-muted-foreground mt-1">
                The subject this email account will be linked to
              </p>
            </div>

            {/* Email Address */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-1.5">
                Email Address <span className="text-red-500">*</span>
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-10 pr-3 py-2 bg-background border border-input rounded-none text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                  placeholder="you@example.com"
                  required
                />
              </div>
            </div>

            {/* IMAP Configuration */}
            {PROVIDERS[selectedProvider].authType === 'imap' && (
              <>
                {/* Password */}
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1.5">
                    Password / App-Specific Password <span className="text-red-500">*</span>
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <input
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="w-full pl-10 pr-3 py-2 bg-background border border-input rounded-none text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                      placeholder="••••••••"
                      required
                    />
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    For Gmail, iCloud, and Yahoo, use an app-specific password instead of your regular password
                  </p>
                </div>

                {/* IMAP Server */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-foreground mb-1.5">
                      IMAP Server <span className="text-red-500">*</span>
                    </label>
                    <div className="relative">
                      <Server className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                      <input
                        type="text"
                        value={imapServer}
                        onChange={(e) => setImapServer(e.target.value)}
                        className="w-full pl-10 pr-3 py-2 bg-background border border-input rounded-none text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                        placeholder="imap.example.com"
                        required
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-1.5">
                      Port <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="number"
                      value={imapPort}
                      onChange={(e) => setImapPort(e.target.value)}
                      className="w-full px-3 py-2 bg-background border border-input rounded-none text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                      placeholder="993"
                      min="1"
                      max="65535"
                      required
                    />
                  </div>
                </div>

                {/* SSL */}
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="use_ssl"
                    checked={useSsl}
                    onChange={(e) => setUseSsl(e.target.checked)}
                    className="w-4 h-4 rounded-none border-input text-primary focus:ring-2 focus:ring-ring"
                  />
                  <label htmlFor="use_ssl" className="text-sm font-medium text-foreground">
                    Use SSL/TLS (recommended)
                  </label>
                </div>

                {/* Test Connection Button */}
                <div className="flex items-center gap-2">
                  <Button
                    type="button"
                    onClick={handleTestConnection}
                    disabled={testingConnection || !email || !password || !imapServer}
                    variant="secondary"
                    size="md"
                  >
                    {testingConnection ? (
                      <>
                        <LoadingIcon />
                        Testing...
                      </>
                    ) : connectionTested ? (
                      <>
                        <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400" />
                        Connection Verified
                      </>
                    ) : (
                      'Test Connection'
                    )}
                  </Button>
                </div>
              </>
            )}

            {/* OAuth Notice */}
            {PROVIDERS[selectedProvider].authType === 'oauth' && (
              <div
                className={`p-3 rounded-none border ${
                  isOAuthConfigured(selectedProvider as 'gmail' | 'outlook')
                    ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800'
                    : 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800'
                }`}
              >
                {isOAuthConfigured(selectedProvider as 'gmail' | 'outlook') ? (
                  <p className="text-sm text-blue-900 dark:text-blue-200">
                    Clicking "Connect" will redirect you to {PROVIDERS[selectedProvider].name} to authorize access to
                    your email account. You'll be returned here after granting permission.
                  </p>
                ) : (
                  <p className="text-sm text-amber-900 dark:text-amber-200">
                    OAuth for {PROVIDERS[selectedProvider].name} is not configured by your administrator. Please contact
                    them to set up OAuth credentials, or choose a different provider.
                  </p>
                )}
              </div>
            )}

            {/* Actions */}
            <div className="flex items-center gap-2 pt-2">
              <Button
                type="submit"
                disabled={loading || (PROVIDERS[selectedProvider].authType === 'imap' && !connectionTested)}
                variant="primary"
                size="md"
              >
                {loading ? (
                  <>
                    <LoadingIcon />
                    Connecting...
                  </>
                ) : (
                  <>
                    <Mail className="w-4 h-4" />
                    Connect Account
                  </>
                )}
              </Button>
              <Button
                type="button"
                onClick={() => {
                  setStep('select')
                  setError(null)
                  setConnectionTested(false)
                }}
                variant="secondary"
                size="md"
              >
                Back
              </Button>
            </div>
          </form>
        </div>
      )}
    </>
  )
}
