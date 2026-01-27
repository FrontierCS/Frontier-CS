#include <bits/stdc++.h>
using namespace std;

struct PairHash {
    size_t operator()(const uint64_t &x) const {
        return std::hash<uint64_t>()(x);
    }
};

int n;
unordered_map<uint64_t, int, PairHash> cacheOR;

int ask(int i, int j) {
    if (i == j) return 0; // not used
    if (i > j) swap(i, j);
    uint64_t key = ((uint64_t)i << 21) | (uint64_t)j; // n <= 2048, 11 bits; use 21 shift safely
    auto it = cacheOR.find(key);
    if (it != cacheOR.end()) return it->second;

    cout << "? " << i << " " << j << endl;
    cout.flush();
    int ans;
    if (!(cin >> ans)) exit(0);
    cacheOR[key] = ans;
    return ans;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    if (!(cin >> n)) return 0;

    if (n == 1) {
        cout << "! 0" << endl;
        cout.flush();
        return 0;
    }

    int cur = 1;
    vector<int> q(n + 1, -1);

    for (int j = 1; j <= n; ++j) {
        if (j == cur) continue;
        q[j] = ask(cur, j);
    }

    int minVal = INT_MAX;
    for (int j = 1; j <= n; ++j) if (j != cur) minVal = min(minVal, q[j]);
    vector<int> S;
    for (int j = 1; j <= n; ++j) if (j != cur && q[j] == minVal) S.push_back(j);

    // Narrow down S until we (hopefully) get the zero index
    // Maintain the invariant that S contains the zero index.
    while ((int)S.size() > 1) {
        bool shrinked = false;
        for (int pi = 0; pi < (int)S.size(); ++pi) {
            int pivot = S[pi];
            int min2 = INT_MAX;
            vector<pair<int,int>> vals; // (j, val)
            vals.reserve(S.size());
            for (int v : S) {
                if (v == pivot) continue;
                int w = ask(pivot, v);
                vals.emplace_back(v, w);
                if (w < min2) min2 = w;
            }
            vector<int> newS;
            newS.push_back(pivot); // pivot always subset-of itself
            for (auto &pr : vals) {
                if (pr.second == min2) newS.push_back(pr.first);
            }
            if ((int)newS.size() < (int)S.size()) {
                S.swap(newS);
                shrinked = true;
                break;
            }
        }
        if (!shrinked) break; // should not happen, but avoid infinite loop
    }

    int zero = S.empty() ? cur : S[0];
    vector<int> p(n + 1, -1);
    p[zero] = 0;
    for (int i = 1; i <= n; ++i) {
        if (i == zero) continue;
        p[i] = ask(zero, i);
    }

    cout << "!";
    for (int i = 1; i <= n; ++i) cout << " " << p[i];
    cout << endl;
    cout.flush();
    return 0;
}