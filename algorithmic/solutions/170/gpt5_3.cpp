#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    long long L;
    if (!(cin >> N >> L)) return 0;
    vector<long long> T(N);
    for (int i = 0; i < N; ++i) cin >> T[i];

    // Sort T with indices
    vector<pair<long long,int>> tp(N);
    for (int i = 0; i < N; ++i) tp[i] = {T[i], i};
    sort(tp.begin(), tp.end());
    vector<long long> sortedT(N);
    vector<int> sortedIdx(N);
    for (int i = 0; i < N; ++i) {
        sortedT[i] = tp[i].first;
        sortedIdx[i] = tp[i].second;
    }
    // Prefix sums for fast range sum
    vector<long double> pref(N+1, 0.0L);
    for (int i = 0; i < N; ++i) pref[i+1] = pref[i] + (long double)sortedT[i];

    auto sumRange = [&](int l, int r) -> long double {
        if (l >= r) return 0.0L;
        return pref[r] - pref[l];
    };
    auto sumAbsRange = [&](int l, int r, long double c) -> long double {
        if (l >= r) return 0.0L;
        // idx: first position > c
        int idx = upper_bound(sortedT.begin(), sortedT.end(), (long long)floor(c)) - sortedT.begin();
        // But c can be non-integer; handle correctly: use upper_bound with long double by custom
        // Implement manual upper_bound for long double comparison
        int lo = 0, hi = N;
        while (lo < hi) {
            int mid = (lo + hi) >> 1;
            if ((long double)sortedT[mid] <= c) lo = mid + 1;
            else hi = mid;
        }
        idx = lo;
        int j = max(l, min(idx, r));
        long double left = c * (j - l) - sumRange(l, j);
        long double right = sumRange(j, r) - c * (r - j);
        return left + right;
    };

    // Search best triple (M, n1, g1)
    // M: number of heavies (50..N)
    // n1: number of heavies with s=1 (self-loop), 0..M
    // B = N - M lights
    // g1: number of lights assigned to s=1 heavies (0..min(B, n1))
    // g0 = B - g1 must be <= n0 = M - n1
    long double bestE = 1e100L;
    int bestM = N, bestN1 = 0, bestG1 = 0;
    long double bestX = (long double)L / (long double)N; // default
    for (int M = max(50, 0); M <= N; ++M) {
        int B = N - M;
        for (int n1 = 0; n1 <= M; ++n1) {
            int n0 = M - n1;
            int g1_min = max(0, B - n0);
            int g1_max = min(B, n1);
            if (g1_min > g1_max) continue;
            for (int g1 = g1_min; g1 <= g1_max; ++g1) {
                int g0 = B - g1;
                // Denominator D = n0 + 2*n1 + 0.5*g0 + 1.0*g1
                long double D = (long double)n0 + 2.0L*(long double)n1 + 0.5L*(long double)g0 + 1.0L*(long double)g1;
                if (D <= 0) continue;
                long double X = (long double)L / D;
                long double v05 = 0.5L * X;
                long double v1 = X;
                long double v2 = 2.0L * X;
                // E0: bottom g0 to v05
                // E2: top n1 to v2
                // E1: middle to v1
                int k0 = g0;
                int k2 = n1;
                if (k0 < 0 || k2 < 0 || k0 + k2 > N) continue;
                long double E0 = sumAbsRange(0, k0, v05);
                long double E2 = sumAbsRange(N - k2, N, v2);
                long double E1 = sumAbsRange(k0, N - k2, v1);
                long double E = E0 + E1 + E2;
                if (E < bestE) {
                    bestE = E;
                    bestM = M;
                    bestN1 = n1;
                    bestG1 = g1;
                    bestX = X;
                }
            }
        }
    }

    // Construct assignment based on best triple
    int M = bestM;
    int B = N - M;
    int n1 = bestN1;
    int n0 = M - n1;
    int g1 = bestG1;
    int g0 = B - g1;
    long double X = bestX;

    // Indices:
    // bottom g0 -> lights with value 0.5X
    // top n1 -> heavies s=1 with value 2X
    // middle N - g0 - n1 -> value X (split into heavies s=0 count n0 and lights X count g1)
    vector<int> L05_ids, L1_ids, H1_ids, H0_ids;
    L05_ids.reserve(g0);
    L1_ids.reserve(g1);
    H1_ids.reserve(n1);
    H0_ids.reserve(n0);

    for (int i = 0; i < g0; ++i) L05_ids.push_back(sortedIdx[i]);
    for (int i = N - n1; i < N; ++i) H1_ids.push_back(sortedIdx[i]);
    // middle:
    vector<int> mid_ids;
    for (int i = g0; i < N - n1; ++i) mid_ids.push_back(sortedIdx[i]);
    // Choose first n0 as heavies s=0, rest g1 as lights X
    for (int i = 0; i < (int)mid_ids.size(); ++i) {
        if ((int)H0_ids.size() < n0) H0_ids.push_back(mid_ids[i]);
        else L1_ids.push_back(mid_ids[i]);
    }

    // Ensure sizes
    if ((int)H0_ids.size() != n0) {
        // Adjust if necessary
        while ((int)H0_ids.size() < n0 && !L1_ids.empty()) {
            H0_ids.push_back(L1_ids.back());
            L1_ids.pop_back();
        }
        while ((int)L1_ids.size() < g1 && !H0_ids.empty() && (int)H0_ids.size() > n0) {
            L1_ids.push_back(H0_ids.back());
            H0_ids.pop_back();
        }
    }
    // Now assign heavies ring: combine H1 then H0
    vector<int> heavies;
    heavies.reserve(M);
    for (int id : H1_ids) heavies.push_back(id);
    for (int id : H0_ids) heavies.push_back(id);
    // In rare case where M < 1 (shouldn't for M>=50), handle separately
    if (heavies.empty()) {
        // Fallback trivial mapping: next ring
        vector<int> a(N), b(N);
        for (int i = 0; i < N; ++i) {
            a[i] = b[i] = (i + 1) % N;
        }
        for (int i = 0; i < N; ++i) {
            cout << a[i] << " " << b[i] << "\n";
        }
        return 0;
    }

    // Choose gates: s=1 heavies will gate g1 lights; s=0 heavies will gate g0 lights
    vector<int> H1_gate_ids, H1_nogate_ids;
    vector<int> H0_gate_ids, H0_nogate_ids;
    // Simple: first g1 of H1_ids gate
    for (int i = 0; i < (int)H1_ids.size(); ++i) {
        if ((int)H1_gate_ids.size() < g1) H1_gate_ids.push_back(H1_ids[i]);
        else H1_nogate_ids.push_back(H1_ids[i]);
    }
    // First g0 of H0_ids gate
    for (int i = 0; i < (int)H0_ids.size(); ++i) {
        if ((int)H0_gate_ids.size() < g0) H0_gate_ids.push_back(H0_ids[i]);
        else H0_nogate_ids.push_back(H0_ids[i]);
    }

    // Pair lights with gates
    // L1_ids with H1_gate_ids; L05_ids with H0_gate_ids
    // Sort both by T values proximity to predicted values could be done, but simple sequential pairing suffices
    // Build mapping: for each heavy gate id -> assigned light id
    unordered_map<int,int> gateLight; gateLight.reserve(N*2);
    for (int i = 0; i < (int)H1_gate_ids.size() && i < (int)L1_ids.size(); ++i) {
        gateLight[H1_gate_ids[i]] = L1_ids[i];
    }
    for (int i = 0; i < (int)H0_gate_ids.size() && i < (int)L05_ids.size(); ++i) {
        gateLight[H0_gate_ids[i]] = L05_ids[i];
    }

    // Build ring next mapping for heavies
    int Msize = (int)heavies.size();
    vector<int> nextHeavy(N, -1), posInRing(N, -1);
    for (int i = 0; i < Msize; ++i) {
        posInRing[heavies[i]] = i;
    }
    for (int i = 0; i < Msize; ++i) {
        int h = heavies[i];
        int nh = heavies[(i + 1) % Msize];
        nextHeavy[h] = nh;
    }

    // For quick check which heavy is s=1 (in H1)
    vector<char> isS1(N, 0), isHeavy(N, 0);
    for (int id : H1_ids) isS1[id] = 1;
    for (int id : heavies) isHeavy[id] = 1;

    // For each light, we need to know its assigned heavy to set return to that heavy's next heavy
    vector<int> lightAssignedHeavy(N, -1);
    for (auto &kv : gateLight) {
        int h = kv.first;
        int lj = kv.second;
        lightAssignedHeavy[lj] = h;
    }
    // In case there are leftover lights (should not happen), assign them to some heavy to ensure valid edges
    vector<int> allLightIds;
    allLightIds.insert(allLightIds.end(), L1_ids.begin(), L1_ids.end());
    allLightIds.insert(allLightIds.end(), L05_ids.begin(), L05_ids.end());
    for (int lj : allLightIds) {
        if (lightAssignedHeavy[lj] == -1) {
            // Assign to some heavy (choose one with smallest index)
            lightAssignedHeavy[lj] = heavies[0];
        }
    }

    // Build a_i, b_i
    vector<int> a(N, 0), b(N, 0);
    // Initialize with simple ring to ensure valid
    for (int i = 0; i < N; ++i) {
        a[i] = b[i] = (i + 1) % N;
    }
    // Heavies
    for (int h : heavies) {
        int nh = nextHeavy[h];
        auto it = gateLight.find(h);
        bool hasLight = (it != gateLight.end());
        if (isS1[h]) {
            // s=1: a = self, b = light or next heavy
            a[h] = h;
            b[h] = hasLight ? it->second : nh;
        } else {
            // s=0: a = next heavy, b = light or next heavy
            a[h] = nh;
            b[h] = hasLight ? it->second : nh;
        }
    }
    // Lights
    for (int lj : allLightIds) {
        int h = lightAssignedHeavy[lj];
        int nh = nextHeavy[h];
        a[lj] = nh;
        b[lj] = nh;
    }

    // Output
    for (int i = 0; i < N; ++i) {
        // Clamp to [0, N-1]
        int ai = a[i];
        int bi = b[i];
        if (ai < 0 || ai >= N) ai = (i + 1) % N;
        if (bi < 0 || bi >= N) bi = (i + 1) % N;
        cout << ai << " " << bi << "\n";
    }
    return 0;
}