<script setup>
import { ref, computed } from 'vue'
import { Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  BarElement,
  CategoryScale,
  LinearScale,
} from 'chart.js'

ChartJS.register(Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale)

const EXAMPLE_QUESTIONS = [
  'How many tracks are there?',
  'Which five artists generated the most sales?',
  'Which country generated the most revenue?',
  'What was the total revenue by year?',
  'Which genre sold the most tracks?',
]

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

const question = ref('')
const result = ref(null)
const error = ref('')
const loading = ref(false)

function isNumeric(value) {
  if (typeof value === 'number') return Number.isFinite(value)
  if (typeof value === 'string' && value.trim() !== '') return Number.isFinite(Number(value))
  return false
}

// Chartable: exactly one category column and one numeric value column.
const chartData = computed(() => {
  if (!result.value) return null
  const { columns, rows } = result.value
  if (columns.length !== 2 || !rows.length) return null
  if (!rows.every((row) => isNumeric(row[1]))) return null

  const accent = getComputedStyle(document.documentElement)
    .getPropertyValue('--accent')
    .trim()

  return {
    labels: rows.map((row) => String(row[0])),
    datasets: [
      {
        label: columns[1],
        data: rows.map((row) => Number(row[1])),
        backgroundColor: accent || '#aa3bff',
      },
    ],
  }
})

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
}

async function ask() {
  if (!question.value.trim() || loading.value) return

  loading.value = true
  error.value = ''
  result.value = null

  try {
    const response = await fetch(`${API_BASE_URL}/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: question.value.trim() }),
    })

    if (!response.ok) {
      const body = await response.json().catch(() => null)
      throw new Error(body?.detail ?? `Request failed (${response.status})`)
    }

    result.value = await response.json()
  } catch (err) {
    error.value = err.message || 'Something went wrong.'
  } finally {
    loading.value = false
  }
}

function askExample(example) {
  if (loading.value) return
  question.value = example
  ask()
}
</script>

<template>
  <main id="app">
    <h1>Chat With Your Data</h1>
    <p class="subtitle">Ask a question about the Chinook sample database.</p>
    <p class="schema-hint">
      Dataset includes artists, albums, tracks, customers, invoices, employees, and
      genres.
    </p>

    <form class="ask-form" @submit.prevent="ask">
      <input
        v-model="question"
        type="text"
        placeholder="e.g. Which five artists generated the most sales?"
        :disabled="loading"
      />
      <button type="submit" :disabled="loading">
        {{ loading ? 'Asking…' : 'Ask' }}
      </button>
    </form>

    <div class="examples">
      <span class="examples-label">Try:</span>
      <button
        v-for="example in EXAMPLE_QUESTIONS"
        :key="example"
        type="button"
        class="example"
        :disabled="loading"
        @click="askExample(example)"
      >
        {{ example }}
      </button>
    </div>

    <section v-if="loading" class="status">
      <p class="loading">Generating SQL, checking it, and querying the database…</p>
    </section>

    <section v-else-if="error" class="status status-error">
      <p>
        I couldn’t answer that one. Try rephrasing it or asking about artists,
        albums, tracks, invoices, customers, or genres.
      </p>
      <p class="detail">{{ error }}</p>
    </section>

    <section v-else-if="result" class="result">
      <div class="block">
        <h2>Answer</h2>
        <p class="answer">{{ result.answer }}</p>
      </div>

      <div v-if="!result.refused" class="block">
        <h2>Results</h2>
        <div v-if="chartData" class="chart-wrap">
          <Bar :data="chartData" :options="chartOptions" />
        </div>
        <div v-if="result.rows.length" class="table-wrap">
          <table>
            <thead>
              <tr>
                <th v-for="column in result.columns" :key="column">{{ column }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, i) in result.rows" :key="i">
                <td v-for="(value, j) in row" :key="j">{{ value }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-else class="empty">No rows returned.</p>
      </div>

      <div v-if="result.sql" class="block">
        <details>
          <summary>Generated SQL</summary>
          <pre><code>{{ result.sql }}</code></pre>
        </details>
      </div>
    </section>

    <section v-else class="status status-hint">
      <p>Try asking about sales, customers, tracks, albums, or genres.</p>
    </section>
  </main>
</template>

<style scoped>
#app {
  max-width: 720px;
  margin: 0 auto;
  padding: 48px 20px;
}

.subtitle {
  margin-bottom: 4px;
}

.schema-hint {
  font-size: 13px;
  color: var(--text);
  opacity: 0.75;
  margin-bottom: 28px;
}

.ask-form {
  display: flex;
  gap: 8px;
}

input {
  flex: 1;
  font-size: 16px;
  font-family: var(--sans);
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg);
  color: var(--text-h);
}

input:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 1px;
}

button {
  font-size: 16px;
  font-family: var(--sans);
  padding: 10px 18px;
  border: none;
  border-radius: 6px;
  background: var(--accent);
  color: #fff;
  cursor: pointer;
  white-space: nowrap;
}

button:disabled {
  opacity: 0.6;
  cursor: default;
}

.examples {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
}

.examples-label {
  font-size: 13px;
  color: var(--text);
  opacity: 0.75;
}

.example {
  font-size: 13px;
  font-family: var(--sans);
  padding: 6px 12px;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--code-bg);
  color: var(--text-h);
  cursor: pointer;
  white-space: nowrap;
}

.example:hover:not(:disabled) {
  border-color: var(--accent);
}

.example:disabled {
  opacity: 0.5;
  cursor: default;
}

.status {
  margin-top: 28px;
  text-align: left;
}

.loading {
  color: var(--text);
  animation: pulse 1.4s ease-in-out infinite;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 0.5;
  }
  50% {
    opacity: 1;
  }
}

.status-error {
  padding: 12px 14px;
  border-radius: 6px;
  background: var(--danger-bg);
  color: var(--danger);
}

.status-error .detail {
  margin-top: 6px;
  font-size: 13px;
  opacity: 0.8;
}

.status-hint {
  color: var(--text);
  opacity: 0.75;
}

.result {
  margin-top: 28px;
  text-align: left;
}

.block {
  margin-bottom: 24px;
}

.answer {
  font-size: 18px;
  color: var(--text-h);
}

details summary {
  cursor: pointer;
  color: var(--text-h);
  font-weight: 600;
  font-size: 16px;
}

pre {
  margin: 8px 0 0;
  padding: 12px;
  border-radius: 6px;
  background: var(--code-bg);
  overflow-x: auto;
}

.chart-wrap {
  height: 280px;
  margin-bottom: 16px;
  padding: 16px;
  border: 1px solid var(--border);
  border-radius: 6px;
}

.table-wrap {
  overflow-x: auto;
  border: 1px solid var(--border);
  border-radius: 6px;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 15px;
}

th,
td {
  text-align: left;
  padding: 8px 10px;
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}

tr:last-child td {
  border-bottom: none;
}

th {
  color: var(--text-h);
}

.empty {
  color: var(--text);
}
</style>
