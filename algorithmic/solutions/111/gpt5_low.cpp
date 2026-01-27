#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    long long n;
    if(!(cin >> n)) return 0;
    int target = (int)floor(sqrt((long double)n / 2.0));
    if (target <= 0) {
        // Handle very small n
        cout << 1 << "\n1\n";
        return 0;
    }
    // Greedy randomized construction
    vector<int> S;
    S.reserve(target);
    unordered_set<int> seen;
    seen.reserve((size_t)target * (target - 1) / 2 * 2);
    vector<unsigned char> used;
    if (n <= 20000000) used.assign((size_t)n + 1, 0);

    std::mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    auto rnd = [&](int l, int r)->int{
        uniform_int_distribution<int> dist(l, r);
        return dist(rng);
    };

    int attemptsLimit = max(1000, target * 50);
    int restarts = 3;
    vector<int> bestS;

    while (restarts-- >= 0) {
        S.clear();
        seen.clear();
        if (!used.empty()) fill(used.begin(), used.end(), 0);

        int attempts = 0;
        while ((int)S.size() < target && attempts < attemptsLimit) {
            ++attempts;
            int x;
            // Try to pick a new random candidate not used
            for (int tries = 0; tries < 50; ++tries) {
                x = rnd(1, (int)n);
                if (used.empty() || !used[x]) break;
            }
            if (!used.empty() && used[x]) {
                // fallback linear scan to find unused
                for (int y = 1; y <= n; ++y) {
                    if (!used[y]) { x = y; break; }
                }
                if (used[x]) continue;
            }

            bool ok = true;
            for (int s : S) {
                int vx = x ^ s;
                if (seen.find(vx) != seen.end()) { ok = false; break; }
            }
            if (!ok) continue;
            // accept
            for (int s : S) seen.insert(x ^ s);
            S.push_back(x);
            if (!used.empty()) used[x] = 1;
        }
        if ((int)S.size() > (int)bestS.size()) bestS = S;
        if ((int)S.size() >= target) break;
    }

    // If still short (very unlikely), reduce to achievable size
    if ((int)bestS.size() < target) {
        // Try to greedily improve by local search with limited time
        S = bestS;
        unordered_set<int> curSeen;
        curSeen.reserve((size_t)S.size() * (S.size() - 1));
        for (size_t i = 0; i < S.size(); ++i)
            for (size_t j = 0; j < i; ++j)
                curSeen.insert(S[i] ^ S[j]);

        int attempts = 0, attemptsLimit2 = 200000;
        while ((int)S.size() < target && attempts < attemptsLimit2) {
            ++attempts;
            int x = (n > 0 ? (int)((rng() % n) + 1) : 1);
            bool dup = false;
            for (int y : S) if (y == x) { dup = true; break; }
            if (dup) continue;
            bool ok = true;
            for (int s : S) {
                int vx = x ^ s;
                if (curSeen.find(vx) != curSeen.end()) { ok = false; break; }
            }
            if (!ok) continue;
            for (int s : S) curSeen.insert(x ^ s);
            S.push_back(x);
        }
        if ((int)S.size() > (int)bestS.size()) bestS = S;
    }

    if ((int)bestS.size() == 0) {
        // Fallback
        cout << 1 << "\n1\n";
        return 0;
    }

    cout << bestS.size() << "\n";
    for (size_t i = 0; i < bestS.size(); ++i) {
        if (i) cout << ' ';
        cout << bestS[i];
    }
    cout << "\n";
    return 0;
}