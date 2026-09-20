# Krahasimi i Modeleve — Leaderboard

_Gjeneruar_: `2026-07-19T12:28:01.106923+00:00`  ·  _gjurma e të dhënave_: `03e8f6b3d597540b`  ·  konfigurime të dështuara: 0

## Protokolli

* **Të pambikëqyrur**: AUC proxy ndaj etiketave të rregullave (pragje 0.4 dhe 0.7), precision@500 ndaj etiketave strikte, Spearman me `rule_score`, stabilitet bootstrap (Jaccard i bashkësive top-5 % mbi ri-përshtatje në 80 % mostra), konsistencë seed-esh për familjet stokastike.
* **Formula e renditjes**: `0.45×proxy_auc_07 + 0.35×stability_jaccard + 0.20×seed_consistency`.
* **Përsëritjet**: 4 ri-përshtatje bootstrap dhe 2 seeds shtesë për familjet stokastike; këto janë kontrolle të kufizuara përsëritshmërie, jo intervale pasigurie.
* **Të mbikëqyrur**: CV e shtresëzuar 5-fold × 2 seeds (ROC-AUC, PR-AUC, Brier) + kontroll kohor i besnikërisë ndaj rregullave (trajnim ≤ 2023, test ≥ 2024) + ECE e kalibrimit.

## ⚠️ Kufizime metodologjike (lexo para përdorimit)

1. Etiketat proxy vijnë nga shtresa e rregullave — metrikat masin **pajtimin me rregullat**, jo mashtrimin real. Asnjë model këtu nuk 'zbulon mashtrim'; ato renditin rekorde tenderi për **rishikim njerëzor**.
2. Ndarja kohore përdor të njëjtat etiketa proxy të derivuara nga rregullat dhe veçori që mbivendosen fort me to. Prandaj OOT mat vetëm besnikëri kohore ndaj proxy-t; nuk mat gjeneralizim të zbulimit. Disa statistika kontekstuale llogariten mbi snapshot-in e plotë.
3. Stabiliteti dhe konsistenca e seed-eve ndihmojnë të vlerësohet riprodhueshmëria e renditjes në këtë snapshot; ato nuk tregojnë saktësi rezultati ose gatishmëri për përdorim operacional.
4. Skenarët alternativë të peshave dhe renditja precision@K më poshtë janë ndjeshmëri e renditjes ndaj proxy-ve, jo validim ndaj rezultateve të jashtme.

## Detektorët e pambikëqyrur (renditur sipas pikës së përbërë)

| Modeli                     | Parametrat            |   Pika e përbërë |   AUC(0.7) |   AUC(0.4) |   Prec@500 |   Stabiliteti |   Konsist. seed |   Spearman(rregulla) |   Koha e trajnimit (s) |
|:---------------------------|:----------------------|-----------------:|-----------:|-----------:|-----------:|--------------:|----------------:|---------------------:|-----------------------:|
| One-Class SVM              | {"nu": 0.1}           |           0.9272 |     0.9101 |     0.8209 |      0.002 |        0.9095 |          0.9969 |               0.2085 |                   0.74 |
| One-Class SVM              | {"nu": 0.05}          |           0.9012 |     0.9164 |     0.8178 |      0.002 |        0.8307 |          0.9904 |               0.2563 |                   0.46 |
| Isolation Forest           | {"n_estimators": 500} |           0.8977 |     0.9115 |     0.8925 |      0     |        0.8244 |          0.9951 |              -0.0098 |                   1.82 |
| HBOS (histogram)           | {"n_bins": 50}        |           0.8761 |     0.8439 |     0.8479 |      0     |        0.8468 |          1      |              -0.2735 |                   0.21 |
| Isolation Forest           | {"n_estimators": 300} |           0.8742 |     0.9051 |     0.8845 |      0     |        0.7673 |          0.9917 |              -0.0065 |                   1.16 |
| Distanca KNN               | {"n_neighbors": 20}   |           0.8721 |     0.8494 |     0.8923 |      0.002 |        0.8335 |          0.9905 |              -0.2553 |                   0.17 |
| One-Class SVM              | {"nu": 0.03}          |           0.8684 |     0.8989 |     0.7588 |      0.002 |        0.764  |          0.9827 |               0.319  |                   0.38 |
| Distanca KNN               | {"n_neighbors": 10}   |           0.859  |     0.8488 |     0.8968 |      0.002 |        0.8015 |          0.9826 |              -0.2731 |                   0.2  |
| Gaussian Mixture (GMM)     | {"n_components": 8}   |           0.8542 |     0.9048 |     0.9199 |      0.006 |        0.7919 |          0.8494 |               0.039  |                  11.3  |
| Gaussian Mixture (GMM)     | {"n_components": 2}   |           0.852  |     0.7218 |     0.8143 |      0.002 |        0.9398 |          0.9912 |               0.1455 |                   1.06 |
| HBOS (histogram)           | {"n_bins": 20}        |           0.8504 |     0.854  |     0.7663 |      0     |        0.7602 |          1      |              -0.1379 |                   0.2  |
| Isolation Forest           | {"n_estimators": 100} |           0.8496 |     0.9239 |     0.8845 |      0.004 |        0.6847 |          0.971  |              -0.0116 |                   0.53 |
| Distanca KNN               | {"n_neighbors": 5}    |           0.8391 |     0.8435 |     0.8973 |      0.002 |        0.76   |          0.9678 |              -0.2816 |                   0.2  |
| Gabimi i rindërtimit PCA   | {"n_components": 10}  |           0.8214 |     0.7278 |     0.7408 |      0     |        0.8397 |          1      |               0.0622 |                   2.16 |
| Local Outlier Factor (LOF) | {"n_neighbors": 100}  |           0.8173 |     0.8713 |     0.8931 |      0.002 |        0.6435 |          1      |              -0.0071 |                   2.81 |
| HBOS (histogram)           | {"n_bins": 10}        |           0.8117 |     0.8749 |     0.7076 |      0     |        0.6226 |          1      |               0.0129 |                   0.21 |
| Local Outlier Factor (LOF) | {"n_neighbors": 50}   |           0.8045 |     0.8833 |     0.8962 |      0.004 |        0.5915 |          1      |               0.0062 |                   2.65 |
| Elliptic Envelope          | {}                    |           0.7952 |     0.8503 |     0.9055 |      0.002 |        0.6079 |          0.9993 |              -0.0911 |                   3.34 |
| Gabimi i rindërtimit PCA   | {"n_components": 5}   |           0.7917 |     0.6927 |     0.6855 |      0     |        0.7998 |          1      |               0.0069 |                   1.95 |
| Local Outlier Factor (LOF) | {"n_neighbors": 30}   |           0.7812 |     0.8731 |     0.8796 |      0.004 |        0.538  |          1      |               0.0119 |                   2.59 |
| Gabimi i rindërtimit PCA   | {"n_components": 15}  |           0.7634 |     0.8237 |     0.8137 |      0.002 |        0.5507 |          1      |               0.0533 |                   2.34 |
| Gaussian Mixture (GMM)     | {"n_components": 4}   |           0.7627 |     0.8677 |     0.9102 |      0.004 |        0.5419 |          0.9131 |               0.0472 |                   4.58 |
| Local Outlier Factor (LOF) | {"n_neighbors": 10}   |           0.6654 |     0.7564 |     0.7396 |      0.002 |        0.3571 |          1      |               0.0072 |                   2.66 |

## Klasifikuesit proxy (renditur sipas besnikërisë kohore ROC-AUC)

| Modeli               | Parametrat                                               |   OOT ROC-AUC |   OOT PR-AUC |   OOT ECE |   CV ROC-AUC |   ±std |   CV PR-AUC |   CV Brier |   Koha (s) |
|:---------------------|:---------------------------------------------------------|--------------:|-------------:|----------:|-------------:|-------:|------------:|-----------:|-----------:|
| HistGradientBoosting | {"learning_rate": 0.05, "max_depth": 4, "max_iter": 300} |        1      |       0.9903 |    0.0004 |       1      | 0      |      0.9933 |     0.0003 |      10.06 |
| HistGradientBoosting | {"learning_rate": 0.08, "max_depth": 4, "max_iter": 300} |        1      |       0.9897 |    0.0004 |       1      | 0      |      0.9936 |     0.0003 |       8.34 |
| Random Forest        | {"max_depth": null, "n_estimators": 200}                 |        1      |       0.9919 |    0.0004 |       1      | 0      |      0.9992 |     0.0001 |       6.3  |
| HistGradientBoosting | {"learning_rate": 0.05, "max_depth": 3, "max_iter": 300} |        0.9999 |       0.986  |    0.0011 |       1      | 0      |      0.9944 |     0.0004 |       8.66 |
| HistGradientBoosting | {"learning_rate": 0.08, "max_depth": 3, "max_iter": 300} |        0.9999 |       0.9843 |    0.0004 |       1      | 0      |      0.994  |     0.0003 |       6.51 |
| HistGradientBoosting | {"learning_rate": 0.05, "max_depth": 6, "max_iter": 300} |        0.9999 |       0.9855 |    0.0003 |       1      | 0      |      0.9937 |     0.0003 |      13.32 |
| HistGradientBoosting | {"learning_rate": 0.08, "max_depth": 6, "max_iter": 300} |        0.9999 |       0.9848 |    0.0002 |       1      | 0      |      0.9948 |     0.0003 |      10.41 |
| Random Forest        | {"max_depth": 12, "n_estimators": 200}                   |        0.9999 |       0.9884 |    0.0013 |       1      | 0      |      0.9984 |     0.0002 |       6.32 |
| Extra Trees          | {"n_estimators": 300}                                    |        0.9999 |       0.9652 |    0.0007 |       1      | 0      |      0.9953 |     0.0004 |       6.25 |
| Regresion Logjistik  | {"C": 1.0}                                               |        0.9974 |       0.5452 |    0.0112 |       0.9991 | 0.0003 |      0.6742 |     0.0064 |       3    |
| Regresion Logjistik  | {"C": 10.0}                                              |        0.9972 |       0.5832 |    0.0059 |       0.9992 | 0.0003 |      0.7122 |     0.0045 |       3.1  |
| Regresion Logjistik  | {"C": 0.1}                                               |        0.9967 |       0.4874 |    0.0241 |       0.9987 | 0.0003 |      0.5853 |     0.0108 |       3.13 |

## Kampionët

* **Elliptic Envelope** — parametrat `{}` · pikë e përbërë 0.795
* **Gaussian Mixture (GMM)** — parametrat `{"n_components": 8}` · pikë e përbërë 0.854
* **HBOS (histogram)** ⭐ (në ansambël) — parametrat `{"n_bins": 50}` · pikë e përbërë 0.876
* **Isolation Forest** ⭐ (në ansambël) — parametrat `{"n_estimators": 500}` · pikë e përbërë 0.898
* **Distanca KNN** ⭐ (në ansambël) — parametrat `{"n_neighbors": 20}` · pikë e përbërë 0.872
* **Local Outlier Factor (LOF)** — parametrat `{"n_neighbors": 100}` · pikë e përbërë 0.817
* **One-Class SVM** ⭐ (në ansambël) — parametrat `{"nu": 0.1}` · pikë e përbërë 0.927
* **Gabimi i rindërtimit PCA** — parametrat `{"n_components": 10}` · pikë e përbërë 0.821
* **Klasifikuesi kampion**: HistGradientBoosting `{"learning_rate": 0.05, "max_depth": 4, "max_iter": 300}` · OOT ROC-AUC 1.0
* **Shpjeguesi (SHAP)**: HistGradientBoosting `{"learning_rate": 0.05, "max_depth": 4, "max_iter": 300}` — përdoret vetëm për shpjegime, jo si detektor i pavarur.

## Ndjeshmëria e zgjedhjes (jo validim)

| skenari            | peshat                                                                      | familjet top-K        |   Jaccard vs deklaruara | konfigurime të ndryshuara   |
|:-------------------|:----------------------------------------------------------------------------|:----------------------|------------------------:|:----------------------------|
| balanced           | {"proxy_auc_07": 0.34, "seed_consistency": 0.33, "stability_jaccard": 0.33} | ocsvm, iso, hbos, knn |                  1      | 1                           |
| stability_emphasis | {"proxy_auc_07": 0.3, "seed_consistency": 0.2, "stability_jaccard": 0.5}    | ocsvm, gmm, iso, hbos |                  0.6    | 1                           |
| proxy_emphasis     | {"proxy_auc_07": 0.6, "seed_consistency": 0.15, "stability_jaccard": 0.25}  | ocsvm, iso, gmm, hbos |                  0.6    | 0                           |
| precision@K proxy  | —                                                                           | gmm, iso, lof, ee     |                  0.1429 | —                           |

**Ansambli përfundimtar**: One-Class SVM, Isolation Forest, HBOS (histogram), Distanca KNN + shtresa e rregullave + pika kontekstuale.