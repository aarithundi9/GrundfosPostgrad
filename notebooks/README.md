# Notebooks

One folder per pod. Name files `<initials>_<yyyymmdd>_<topic>.ipynb`
(e.g. `ek_20261119_profile_eda.ipynb`).

Start every notebook with:

```python
%load_ext autoreload
%autoreload 2
from heatreuse import io, config, timeutils, units, metrics
```

Notebooks are for exploring and charts. Anything another person needs goes into
`src/heatreuse/` and a contract table. Strip outputs before committing (`nbstripout --install`).
