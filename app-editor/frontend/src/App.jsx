import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import FilaEdicao from './pages/FilaEdicao'
import ValidarLetra from './pages/ValidarLetra'
import ValidarAlinhamento from './pages/ValidarAlinhamento'
import Conclusao from './pages/Conclusao'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<FilaEdicao />} />
        <Route path="/edicao/:id/letra" element={<ValidarLetra />} />
        <Route path="/edicao/:id/alinhamento" element={<ValidarAlinhamento />} />
        <Route path="/edicao/:id/conclusao" element={<Conclusao />} />
      </Routes>
    </Layout>
  )
}
