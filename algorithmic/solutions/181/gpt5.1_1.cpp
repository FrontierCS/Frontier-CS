#include <bits/stdc++.h>
using namespace std;

int N;
vector<uint8_t> Dmat;
vector<uint8_t> Fmat;

long long computeCost(const vector<int>& p) {
    long long cost = 0;
    for (int i = 0; i < N; ++i) {
        int pi = p[i];
        int offsetDi = pi * N;
        const uint8_t* Frow = &Fmat[i * N];
        for (int j = 0; j < N; ++j) {
            if (Frow[j]) {
                cost += (int)Dmat[offsetDi + p[j]];
            }
        }
    }
    return cost;
}

long long deltaSwap(const vector<int>& p, int a, int b) {
    if (a == b) return 0;
    int pa = p[a];
    int pb = p[b];
    int offset_pa = pa * N;
    int offset_pb = pb * N;
    long long delta = 0;

    for (int k = 0; k < N; ++k) {
        if (k == a || k == b) continue;
        int pk = p[k];
        int offset_pk = pk * N;

        uint8_t Fak = Fmat[a * N + k];
        uint8_t Fka = Fmat[k * N + a];
        uint8_t Fbk = Fmat[b * N + k];
        uint8_t Fkb = Fmat[k * N + b];

        if (Fak) delta += (int)Dmat[offset_pb + pk] - (int)Dmat[offset_pa + pk];
        if (Fka) delta += (int)Dmat[offset_pk + pb] - (int)Dmat[offset_pk + pa];
        if (Fbk) delta += (int)Dmat[offset_pa + pk] - (int)Dmat[offset_pb + pk];
        if (Fkb) delta += (int)Dmat[offset_pk + pa] - (int)Dmat[offset_pk + pb];
    }

    uint8_t Faa = Fmat[a * N + a];
    uint8_t Fbb = Fmat[b * N + b];
    uint8_t Fab = Fmat[a * N + b];
    uint8_t Fba = Fmat[b * N + a];

    if (Faa) delta += (int)Dmat[pb * N + pb] - (int)Dmat[pa * N + pa];
    if (Fbb) delta += (int)Dmat[pa * N + pa] - (int)Dmat[pb * N + pb];
    if (Fab) delta += (int)Dmat[pb * N + pa] - (int)Dmat[pa * N + pb];
    if (Fba) delta += (int)Dmat[pa * N + pb] - (int)Dmat[pb * N + pa];

    return delta;
}

void localSearch(vector<int>& p, long long& cost, mt19937& rng) {
    if (N <= 1) return;
    int iters = min(20000, max(1000, N * 10));
    for (int it = 0; it < iters; ++it) {
        int a = (int)(rng() % N);
        int b = (int)(rng() % N);
        if (a == b) {
            --it;
            continue;
        }
        long long delta = deltaSwap(p, a, b);
        if (delta < 0) {
            swap(p[a], p[b]);
            cost += delta;
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;
    N = n;

    Dmat.assign(N * N, 0);
    Fmat.assign(N * N, 0);

    vector<int> degDout(N, 0), degDin(N, 0);
    vector<int> degFout(N, 0), degFin(N, 0);

    char c;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            cin >> c;
            uint8_t v = (uint8_t)(c - '0');
            Dmat[i * N + j] = v;
            if (v) {
                degDout[i]++;
                degDin[j]++;
            }
        }
    }

    long long totalFlow = 0;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            cin >> c;
            uint8_t v = (uint8_t)(c - '0');
            Fmat[i * N + j] = v;
            if (v) {
                degFout[i]++;
                degFin[j]++;
                totalFlow++;
            }
        }
    }

    vector<int> degD(N), degF(N);
    for (int i = 0; i < N; ++i) {
        degD[i] = degDout[i] + degDin[i];
        degF[i] = degFout[i] + degFin[i];
    }

    vector<int> facilities(N);
    iota(facilities.begin(), facilities.end(), 0);

    vector<int> fAsc = facilities;
    sort(fAsc.begin(), fAsc.end(), [&](int a, int b) {
        if (degF[a] != degF[b]) return degF[a] < degF[b];
        return a < b;
    });
    vector<int> fDesc = fAsc;
    reverse(fDesc.begin(), fDesc.end());

    vector<int> locations(N);
    iota(locations.begin(), locations.end(), 0);

    vector<int> dAsc = locations;
    sort(dAsc.begin(), dAsc.end(), [&](int a, int b) {
        if (degD[a] != degD[b]) return degD[a] < degD[b];
        return a < b;
    });
    vector<int> dDesc = dAsc;
    reverse(dDesc.begin(), dDesc.end());

    vector<int> perm(N), bestPerm(N);
    long long bestCost;

    // Identity permutation
    for (int i = 0; i < N; ++i) perm[i] = i;
    bestCost = computeCost(perm);
    bestPerm = perm;

    // Reverse identity
    for (int i = 0; i < N; ++i) perm[i] = N - 1 - i;
    long long cst = computeCost(perm);
    if (cst < bestCost) {
        bestCost = cst;
        bestPerm = perm;
    }

    auto tryPermutation = [&](const vector<int>& orderF, const vector<int>& orderD) {
        for (int k = 0; k < N; ++k) {
            perm[orderF[k]] = orderD[k];
        }
        long long cst2 = computeCost(perm);
        if (cst2 < bestCost) {
            bestCost = cst2;
            bestPerm = perm;
        }
    };

    if (N > 1) {
        tryPermutation(fDesc, dAsc);
        tryPermutation(fDesc, dDesc);
        tryPermutation(fAsc, dAsc);
        tryPermutation(fAsc, dDesc);
    }

    mt19937 rng(712367);

    // Random permutation candidate
    for (int i = 0; i < N; ++i) perm[i] = i;
    shuffle(perm.begin(), perm.end(), rng);
    cst = computeCost(perm);
    if (cst < bestCost) {
        bestCost = cst;
        bestPerm = perm;
    }

    // Local search improvement
    localSearch(bestPerm, bestCost, rng);

    // Output permutation in 1-based indexing
    for (int i = 0; i < N; ++i) {
        if (i) cout << ' ';
        cout << (bestPerm[i] + 1);
    }
    cout << '\n';

    return 0;
}