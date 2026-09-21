Modelo de trabalho acadêmico do IFC.

O arquivo main.tex tem as referências.

Contribuindo com a iniciativa de Lucas Barbosa (https://github.com/lvbarbosa)

Arquivos adaptados por Eliton Tiago (https://github.com/ElitonTiago)

Toda ajuda é bem vinda :D

## Compilação com Podman

Execute os comandos a partir desta pasta (`latex/`). O serviço usa XeLaTeX,
BibTeX e Makeglossaries para gerar o PDF, as referências e a lista de siglas:

```bash
podman compose run --rm latex
```

O arquivo gerado será `main.pdf` nesta pasta. Para remover somente os arquivos
auxiliares, sem apagar o PDF ou os arquivos-fonte:

```bash
podman compose run --rm clean
```

Em hosts com SELinux, o volume `.:/work:Z` já aplica o relabel necessário.
