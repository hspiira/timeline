/**
 * Seed script to create dummy subjects
 *
 * Usage:
 * 1. Start the backend server (dev/timeline)
 * 2. Login to the UI and get your auth token
 * 3. Run: npx tsx scripts/seed-subjects.ts <AUTH_TOKEN>
 */

const API_URL = process.env.API_URL || 'http://localhost:8000'

interface SubjectData {
  subject_type: string
  external_ref?: string
}

const dummySubjects: SubjectData[] = [
  { subject_type: 'user', external_ref: 'user_john_doe_001' },
  { subject_type: 'user', external_ref: 'user_jane_smith_002' },
  { subject_type: 'user', external_ref: 'user_bob_johnson_003' },
  { subject_type: 'order', external_ref: 'ORD-2024-001' },
  { subject_type: 'order', external_ref: 'ORD-2024-002' },
  { subject_type: 'order', external_ref: 'ORD-2024-003' },
  { subject_type: 'project', external_ref: 'PROJ-ALPHA' },
  { subject_type: 'project', external_ref: 'PROJ-BETA' },
  { subject_type: 'project', external_ref: 'PROJ-GAMMA' },
  { subject_type: 'invoice', external_ref: 'INV-2024-001' },
  { subject_type: 'invoice', external_ref: 'INV-2024-002' },
  { subject_type: 'shipment', external_ref: 'SHIP-FDX-001' },
  { subject_type: 'shipment', external_ref: 'SHIP-UPS-002' },
  { subject_type: 'customer', external_ref: 'CUST-ACME-001' },
  { subject_type: 'customer', external_ref: 'CUST-GLOBEX-002' },
]

async function createSubject(token: string, data: SubjectData) {
  try {
    const response = await fetch(`${API_URL}/subjects/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(data),
    })

    if (!response.ok) {
      const error = await response.text()
      throw new Error(`Failed to create subject: ${error}`)
    }

    const result = await response.json()
    return result
  } catch (error) {
    console.error(`Error creating ${data.subject_type}:`, error)
    throw error
  }
}

async function seedSubjects(token: string) {
  console.log(`🌱 Seeding ${dummySubjects.length} dummy subjects...`)
  console.log(`📡 API URL: ${API_URL}\n`)

  let successCount = 0
  let errorCount = 0

  for (const subject of dummySubjects) {
    try {
      const result = await createSubject(token, subject)
      console.log(`✅ Created ${subject.subject_type}: ${result.id} (${subject.external_ref})`)
      successCount++

      // Small delay to avoid overwhelming the server
      await new Promise(resolve => setTimeout(resolve, 100))
    } catch (error) {
      console.error(`❌ Failed to create ${subject.subject_type}:`, error)
      errorCount++
    }
  }

  console.log(`\n🎉 Seeding complete!`)
  console.log(`   ✅ Success: ${successCount}`)
  console.log(`   ❌ Errors: ${errorCount}`)
}

// Main execution
const token = process.argv[2]

if (!token) {
  console.error('❌ Error: Auth token required')
  console.log('\nUsage:')
  console.log('  npx tsx scripts/seed-subjects.ts <AUTH_TOKEN>')
  console.log('\nTo get your auth token:')
  console.log('  1. Login to the UI')
  console.log('  2. Open browser console')
  console.log('  3. Run: localStorage.getItem("auth_token")')
  process.exit(1)
}

seedSubjects(token)
  .then(() => process.exit(0))
  .catch((error) => {
    console.error('Fatal error:', error)
    process.exit(1)
  })
