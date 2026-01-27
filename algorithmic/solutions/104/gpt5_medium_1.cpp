#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if(!(cin >> t)) return 0;
    const double base = 1.116;
    for(int tc = 0; tc < t; ++tc) {
        int n;
        cin >> n;
        int maxQ = 2 * (int)ceil(log(n) / log(base));
        int usedQ = 0;

        vector<int> alive;
        alive.reserve(n);
        for (int i = 1; i <= n; ++i) alive.push_back(i);

        // For each position, store last two statuses and how many known
        vector<int> d1(n+1, 0), d2(n+1, 0), known(n+1, 0);
        
        auto ask = [&](int l, int r)->int{
            cout << "? " << l << " " << r << endl;
            cout.flush();
            int x;
            if(!(cin >> x)) exit(0);
            usedQ++;
            int len = r - l + 1;
            // s = 1 if x == len-1 (absent inside), else 0
            int s = (x == len - 1) ? 1 : 0;
            return s;
        };
        auto guess = [&](int a)->int{
            cout << "! " << a << endl;
            cout.flush();
            int y;
            if(!(cin >> y)) exit(0);
            return y;
        };

        // Step 1: query full
        if (usedQ < maxQ && (int)alive.size() > 2) {
            int s = ask(1, n);
            // Update known for all alive (all positions inside full range)
            for (int pos : alive) {
                int newd = s ^ 1; // P=1 for full range
                d1[pos] = newd;
                known[pos] = 1;
            }
        }

        // Step 2: query full again
        if (usedQ < maxQ && (int)alive.size() > 2) {
            int s = ask(1, n);
            for (int pos : alive) {
                int newd = s ^ 1; // P=1 for full range
                d2[pos] = newd;
                known[pos] = 2;
            }
        }

        while (usedQ < maxQ && (int)alive.size() > 2) {
            int m = (int)alive.size();

            // Determine forced states (known >=2 and d1==d2)
            vector<int> g1(m, 0), g0(m, 0);
            int F0 = 0, F1 = 0, Ftot = 0, flex = 0;

            for (int idx = 0; idx < m; ++idx) {
                int pos = alive[idx];
                if (known[pos] >= 2) {
                    if (d1[pos] == d2[pos]) {
                        int forcedDnext = 1 - d2[pos];
                        if (forcedDnext == 1) {
                            g1[idx] = 1; F1++;
                        } else {
                            g0[idx] = 1; F0++;
                        }
                        Ftot++;
                    } else {
                        flex++;
                    }
                } else {
                    // known < 2 shouldn't happen beyond initial steps
                    flex++;
                }
            }

            int chooseK = 0;
            if (Ftot == 0) {
                // No forced states; choose half split of alive positions
                chooseK = max(1, m / 2);
            } else {
                // Choose k in [1..m] minimizing worst-case survivors
                vector<int> p1(m+1, 0), p0(m+1, 0);
                for (int i = 0; i < m; ++i) {
                    p1[i+1] = p1[i] + g1[i];
                    p0[i+1] = p0[i] + g0[i];
                }
                int bestK = 1;
                long long bestVal = LLONG_MAX;
                for (int k = 1; k <= m; ++k) {
                    int A = p1[k]; // forced dF=1 inside
                    int B = p0[k]; // forced dF=0 inside
                    int forcedInside = A + (F0 - B);
                    int worstForcedSurvive = max(forcedInside, Ftot - forcedInside);
                    long long totalSurvive = flex + worstForcedSurvive;
                    if (totalSurvive < bestVal) {
                        bestVal = totalSurvive;
                        bestK = k;
                    }
                }
                chooseK = bestK;
            }

            int l = alive[0];
            int r = alive[chooseK - 1];
            if (l > r) swap(l, r);
            int s = ask(l, r);

            // Update/eliminate
            vector<int> newAlive;
            newAlive.reserve(alive.size());
            for (int idx = 0; idx < m; ++idx) {
                int pos = alive[idx];
                int P = (idx < chooseK) ? 1 : 0;
                int newd = s ^ P;
                if (known[pos] < 2) {
                    if (known[pos] == 0) {
                        d1[pos] = newd;
                        known[pos] = 1;
                    } else if (known[pos] == 1) {
                        d2[pos] = newd;
                        known[pos] = 2;
                    }
                    newAlive.push_back(pos);
                } else {
                    bool keep = true;
                    if (d1[pos] == d2[pos]) {
                        int required = 1 - d2[pos];
                        if (newd != required) keep = false;
                    }
                    if (keep) {
                        d1[pos] = d2[pos];
                        d2[pos] = newd;
                        newAlive.push_back(pos);
                    }
                }
            }
            alive.swap(newAlive);
            if ((int)alive.size() <= 2) break;
        }

        // Make up to two guesses
        int a1 = 1, a2 = 1;
        if (!alive.empty()) a1 = alive[0];
        if ((int)alive.size() >= 2) a2 = alive[1];
        else a2 = (a1 == 1 ? 2 : 1);

        int y = guess(a1);
        if (y == 0) {
            guess(a2);
        }
        cout << "#" << endl;
        cout.flush();
    }

    return 0;
}