#include <bits/stdc++.h>
using namespace std;

struct Solver {
    int t;
    Solver() {
        ios::sync_with_stdio(false);
        cin.tie(nullptr);
    }

    // Choose interval [l, r] based on current states
    pair<int,int> choose_interval(const vector<unsigned char>& runlen,
                                  const vector<unsigned char>& lastbit,
                                  const vector<char>& alive,
                                  int n) {
        // Collect positions with runlen == 2
        vector<int> pos;
        vector<int> dv2; // +2 if lastbit==0, -2 if lastbit==1
        int tot0 = 0, tot1 = 0;
        pos.reserve(n);
        dv2.reserve(n);
        for (int i = 1; i <= n; ++i) {
            if (!alive[i]) continue;
            if (runlen[i] == 2) {
                pos.push_back(i);
                if (lastbit[i] == 0) {
                    dv2.push_back(+2);
                    ++tot0;
                } else {
                    dv2.push_back(-2);
                    ++tot1;
                }
            }
        }

        if ((int)pos.size() == 0) {
            // Fallback: split the array roughly in half
            int l = 1;
            int r = max(1, n / 2);
            return {l, r};
        }

        int m = (int)pos.size();
        // Target T2 = tot0 - tot1, and we want subarray sum K2 close to T2
        long long T2 = (long long)tot0 - (long long)tot1;

        // Prefix sums Q2
        vector<long long> Q2(m + 1, 0);
        for (int i = 1; i <= m; ++i) {
            Q2[i] = Q2[i - 1] + dv2[i - 1];
        }

        // Maintain set of prefix sums for i in [0..j-1]
        // We need to find prefix Q2[i] closest to (Q2[j] - T2)
        set<pair<long long,int>> pref;
        pref.insert({Q2[0], 0});

        long long bestDiff = (1LL<<62);
        int bestLBlock = 1, bestRBlock = 1;

        for (int j = 1; j <= m; ++j) {
            long long target = Q2[j] - T2;
            auto it = pref.lower_bound({target, -1});
            if (it != pref.end()) {
                long long K2 = Q2[j] - it->first;
                long long diff = llabs(K2 - T2);
                if (diff < bestDiff) {
                    bestDiff = diff;
                    bestLBlock = it->second + 1; // block i+1..j
                    bestRBlock = j;
                }
            }
            if (it != pref.begin()) {
                auto it2 = prev(it);
                long long K2 = Q2[j] - it2->first;
                long long diff = llabs(K2 - T2);
                if (diff < bestDiff) {
                    bestDiff = diff;
                    bestLBlock = it2->second + 1;
                    bestRBlock = j;
                }
            }
            pref.insert({Q2[j], j});
        }

        int l = pos[bestLBlock - 1];
        int r = pos[bestRBlock - 1];
        if (l > r) swap(l, r);
        // Safety: ensure valid bounds
        l = max(1, min(l, n));
        r = max(1, min(r, n));
        if (l > r) swap(l, r);
        return {l, r};
    }

    void run() {
        if (!(cin >> t)) return;
        for (int _ = 0; _ < t; ++_) {
            int n;
            cin >> n;

            // State arrays 1..n
            vector<unsigned char> runlen(n+1, 0); // 0,1,2
            vector<unsigned char> lastbit(n+1, 0); // 0 or 1
            vector<char> alive(n+1, 1);

            int aliveCount = n;

            // Query limit
            double base = 1.116;
            int qlimit = (int)ceil(log((double)n) / log(base)) * 2;
            if (qlimit <= 0) qlimit = 2 * 10; // safety fallback
            int qUsed = 0;

            // Main loop
            while (aliveCount > 2 && qUsed < qlimit) {
                auto [l, r] = choose_interval(runlen, lastbit, alive, n);
                // Ensure interval valid
                if (l < 1) l = 1;
                if (r > n) r = n;
                if (l > r) swap(l, r);
                // Avoid zero-length consequences; ensure some span
                if (l == 0 || r == 0) { l = 1; r = max(1, n/2); }

                cout << "? " << l << " " << r << "\n";
                cout.flush();

                int x;
                if (!(cin >> x)) return; // in case of I/O failure

                int mlen = r - l + 1;
                int S = x - (mlen - 1); // 0 or 1

                // Update states for all indices
                for (int i = 1; i <= n; ++i) {
                    if (!alive[i]) continue;
                    int inside = (i >= l && i <= r) ? 1 : 0;
                    int b = S ^ inside; // new bit for index i
                    if (runlen[i] == 2 && lastbit[i] == (unsigned char)b) {
                        // triple run -> eliminate
                        alive[i] = 0;
                        --aliveCount;
                    } else {
                        if (runlen[i] == 0) {
                            runlen[i] = 1;
                            lastbit[i] = (unsigned char)b;
                        } else if (lastbit[i] == (unsigned char)b) {
                            runlen[i] = 2;
                            lastbit[i] = (unsigned char)b;
                        } else {
                            runlen[i] = 1;
                            lastbit[i] = (unsigned char)b;
                        }
                    }
                }
                ++qUsed;
            }

            // Collect remaining candidates
            vector<int> cand;
            cand.reserve(aliveCount);
            for (int i = 1; i <= n; ++i) if (alive[i]) cand.push_back(i);

            // Make up to two guesses
            int guessesMade = 0;
            if (!cand.empty()) {
                cout << "! " << cand[0] << "\n";
                cout.flush();
                int y;
                if (!(cin >> y)) return;
                guessesMade++;
                if (y == 1) {
                    cout << "#\n";
                    cout.flush();
                    continue;
                }
            }
            if ((int)cand.size() >= 2) {
                cout << "! " << cand[1] << "\n";
                cout.flush();
                int y;
                if (!(cin >> y)) return;
                guessesMade++;
                // Regardless of y, end test case
                cout << "#\n";
                cout.flush();
            } else {
                // Only one candidate or none
                // If none, guess arbitrary 1 (won't happen in consistent interactor)
                int guess = cand.empty() ? 1 : cand[0];
                if (guessesMade == 0) {
                    cout << "! " << guess << "\n";
                    cout.flush();
                    int y;
                    if (!(cin >> y)) return;
                }
                cout << "#\n";
                cout.flush();
            }
        }
    }
};

int main() {
    Solver s;
    s.run();
    return 0;
}