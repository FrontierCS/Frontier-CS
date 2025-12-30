#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;

        // Precompute query limit
        double base = 1.116;
        int qlimit = (int)ceil(log((double)n) / log(base)) * 2;

        vector<char> alive(n + 1, 1);
        vector<char> last_bit(n + 1, 0); // 0 or 1
        vector<char> last_len(n + 1, 0); // 0 (none), 1, 2
        int alive_cnt = n;

        int qcount = 0;

        auto ask = [&](int l, int r) -> int {
            cout << "? " << l << " " << r << endl;
            cout.flush();
            int x;
            if (!(cin >> x)) exit(0);
            int U = r - l + 1;
            // x must be U or U-1
            int S = (x == U) ? 1 : 0;
            return S;
        };

        auto choose_k = [&](const vector<int>& pref20, const vector<int>& pref21,
                            const vector<int>& pref10, const vector<int>& pref11) -> int {
            int tot20 = pref20[n];
            int tot21 = pref21[n];
            long long bestM2 = -1;
            int bestK2 = -1;
            for (int k = 1; k <= n; ++k) {
                int i20 = pref20[k], i21 = pref21[k];
                int o20 = tot20 - i20, o21 = tot21 - i21;
                long long mIfS0 = (long long)i21 + o20;
                long long mIfS1 = (long long)i20 + o21;
                long long M2 = min(mIfS0, mIfS1);
                if (M2 > bestM2) {
                    bestM2 = M2;
                    bestK2 = k;
                }
            }
            if (bestM2 > 0) return bestK2;

            // If no guaranteed elimination among len==2, try to maximize len1->len2 progress
            int tot10 = pref10[n];
            int tot11 = pref11[n];
            long long bestM1 = -1;
            int bestK1 = -1;
            for (int k = 1; k <= n; ++k) {
                int i10 = pref10[k], i11 = pref11[k];
                int o10 = tot10 - i10, o11 = tot11 - i11;
                long long mIfS0 = (long long)i11 + o10; // inside b=1 + outside b=0
                long long mIfS1 = (long long)i10 + o11; // inside b=0 + outside b=1
                long long M1 = min(mIfS0, mIfS1);
                if (M1 > bestM1) {
                    bestM1 = M1;
                    bestK1 = k;
                }
            }
            if (bestM1 > 0) return bestK1;

            // Otherwise, pick median of alive indices to vary
            int need = (alive_cnt + 1) / 2;
            int cnt = 0, k = n / 2;
            for (int i = 1; i <= n; ++i) {
                if (alive[i]) {
                    ++cnt;
                    if (cnt == need) { k = i; break; }
                }
            }
            if (k < 1) k = 1;
            return k;
        };

        while (alive_cnt > 2 && qcount < qlimit) {
            // Build prefix arrays for len==2 and len==1 grouped by last_bit
            vector<int> pref20(n + 1, 0), pref21(n + 1, 0), pref10(n + 1, 0), pref11(n + 1, 0);
            for (int i = 1; i <= n; ++i) {
                pref20[i] = pref20[i - 1];
                pref21[i] = pref21[i - 1];
                pref10[i] = pref10[i - 1];
                pref11[i] = pref11[i - 1];
                if (!alive[i]) continue;
                if (last_len[i] == 2) {
                    if (last_bit[i] == 0) pref20[i]++;
                    else pref21[i]++;
                } else if (last_len[i] == 1) {
                    if (last_bit[i] == 0) pref10[i]++;
                    else pref11[i]++;
                }
            }

            int k = choose_k(pref20, pref21, pref10, pref11);
            if (k < 1) k = 1;

            int S = ask(1, k);
            ++qcount;

            // Update/eliminate candidates
            for (int i = 1; i <= n; ++i) {
                if (!alive[i]) continue;
                int I = (i <= k) ? 1 : 0;
                int hnew = S ^ I;
                if (last_len[i] == 0) {
                    last_bit[i] = (char)hnew;
                    last_len[i] = 1;
                } else if (last_len[i] == 1) {
                    if (hnew == last_bit[i]) last_len[i] = 2;
                    else { last_bit[i] = (char)hnew; last_len[i] = 1; }
                } else { // last_len==2
                    if (hnew == last_bit[i]) {
                        // Eliminate
                        alive[i] = 0;
                        --alive_cnt;
                    } else {
                        last_bit[i] = (char)hnew;
                        last_len[i] = 1;
                    }
                }
            }
        }

        // Gather remaining candidates
        vector<int> candidates;
        for (int i = 1; i <= n; ++i) if (alive[i]) candidates.push_back(i);

        if (candidates.empty()) {
            // Fallback: guess any two valid positions (1 and 2)
            cout << "! " << 1 << endl;
            cout.flush();
            int y; if (!(cin >> y)) return 0;
            cout << "! " << 2 << endl;
            cout.flush();
            if (!(cin >> y)) return 0;
            cout << "#" << endl;
            cout.flush();
            continue;
        }

        // Make up to two guesses
        int first = candidates[0];
        cout << "! " << first << endl;
        cout.flush();
        int y1; if (!(cin >> y1)) return 0;
        if (y1 == 1) {
            cout << "#" << endl;
            cout.flush();
            continue;
        }

        int second = first;
        if ((int)candidates.size() >= 2) second = candidates[1];
        else {
            // pick any other index different from first
            second = (first == 1 ? 2 : 1);
        }
        cout << "! " << second << endl;
        cout.flush();
        int y2; if (!(cin >> y2)) return 0;

        cout << "#" << endl;
        cout.flush();
    }

    return 0;
}