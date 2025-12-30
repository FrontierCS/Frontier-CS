#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, k;
    long long m;
    string epsStr;
    if (!(cin >> n >> m >> k >> epsStr)) return 0;

    // Parse eps as exact decimal, compute cap = floor((1+eps)*ideal)
    bool hasExp = (epsStr.find('e') != string::npos) || (epsStr.find('E') != string::npos);
    long long ideal = (n + (long long)k - 1) / (long long)k;
    long long cap;
    if (!hasExp) {
        long long ip = 0, frac = 0, scale = 1;
        size_t dot = epsStr.find('.');
        if (dot == string::npos) {
            if (!epsStr.empty())
                ip = stoll(epsStr);
        } else {
            string intPart = epsStr.substr(0, dot);
            string fracPart = epsStr.substr(dot + 1);
            if (!intPart.empty())
                ip = stoll(intPart);
            if (!fracPart.empty()) {
                frac = stoll(fracPart);
                for (size_t i = 0; i < fracPart.size(); ++i) scale *= 10;
            }
        }
        // (1 + eps) = (1 + ip + frac/scale) = ((1+ip)*scale + frac) / scale
        long long num = (1 + ip) * scale + frac;
        long long den = scale;
        __int128 prod = (__int128)num * (__int128)ideal;
        cap = (long long)(prod / den); // floor
    } else {
        long double eps = stold(epsStr);
        long double capLD = (1.0L + eps) * (long double)ideal;
        cap = (long long)floorl(capLD);
    }

    vector<vector<int>> adj(n + 1);
    adj.shrink_to_fit(); // no effect but explicit

    for (long long i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        if (u == v) continue; // ignore self-loops
        if (u < 1 || u > n || v < 1 || v > n) continue; // safety
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    vector<int> part(n + 1);
    vector<int> partSize(k + 1, 0);

    // Initial balanced contiguous assignment
    int base = n / k;
    int rem = n % k;
    int curV = 1;
    for (int p = 1; p <= k; ++p) {
        int cnt = base + (p <= rem ? 1 : 0);
        partSize[p] = cnt;
        for (int i = 0; i < cnt && curV <= n; ++i) {
            part[curV++] = p;
        }
    }

    // Local refinement minimizing edge cut under capacity constraint
    vector<int> order(n);
    iota(order.begin(), order.end(), 1);

    vector<int> freq(k + 1, 0);
    vector<int> usedParts;
    usedParts.reserve(64);

    mt19937_64 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count());

    int maxIter = 2;
    for (int it = 0; it < maxIter; ++it) {
        shuffle(order.begin(), order.end(), rng);
        bool movedAny = false;

        for (int idx = 0; idx < n; ++idx) {
            int v = order[idx];
            const auto &neis = adj[v];
            int deg = (int)neis.size();
            if (deg == 0) continue;

            int curPart = part[v];
            usedParts.clear();

            // Count neighbor parts
            for (int u : neis) {
                int pu = part[u];
                if (freq[pu] == 0) usedParts.push_back(pu);
                ++freq[pu];
            }

            int sameCur = freq[curPart];
            int cutOld = deg - sameCur;
            int bestCut = cutOld;
            int bestPart = curPart;

            for (int pID : usedParts) {
                if (pID == curPart) continue;
                if (partSize[pID] >= cap) continue;
                int sameTarget = freq[pID];
                int cutNew = deg - sameTarget;
                if (cutNew < bestCut) {
                    bestCut = cutNew;
                    bestPart = pID;
                }
            }

            for (int pID : usedParts) freq[pID] = 0;

            if (bestPart != curPart) {
                --partSize[curPart];
                ++partSize[bestPart];
                part[v] = bestPart;
                movedAny = true;
            }
        }

        if (!movedAny) break;
    }

    // Output partition
    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << part[i];
    }
    cout << '\n';

    return 0;
}