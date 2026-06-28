<script setup>
import { ref } from 'vue'

const question = ref('')
const result = ref(null)
const error = ref('')
const loading = ref(false)

async function ask() {
  if (!question.value.trim() || loading.value) return

  loading.value = true
  error.value = ''
  result.value = null

  try {
    const response = await fetch('/ask', {
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
</script>

<template>
  <main id="app">
    <h1>Chat With Your Data</h1>
    <p class="subtitle">Ask a question about the Chinook sample database.</p>

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

    <p v-if="error" class="error">{{ error }}</p>

    <section v-if="result" class="result">
      <p class="answer">{{ result.answer }}</p>

      <details>
        <summary>Generated SQL</summary>
        <pre><code>{{ result.sql }}</code></pre>
      </details>

      <table v-if="result.rows.length">
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
      <p v-else class="empty">No rows returned.</p>
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

.error {
  margin-top: 16px;
  padding: 10px 12px;
  border-radius: 6px;
  background: var(--danger-bg);
  color: var(--danger);
}

.result {
  margin-top: 28px;
  text-align: left;
}

.answer {
  font-size: 18px;
  color: var(--text-h);
  margin-bottom: 16px;
}

details {
  margin-bottom: 16px;
}

summary {
  cursor: pointer;
  color: var(--text);
}

pre {
  margin: 8px 0 0;
  padding: 12px;
  border-radius: 6px;
  background: var(--code-bg);
  overflow-x: auto;
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
}

th {
  color: var(--text-h);
}

.empty {
  color: var(--text);
}
</style>
