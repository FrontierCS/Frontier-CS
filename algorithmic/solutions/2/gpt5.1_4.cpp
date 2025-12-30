#include <bits/stdc++.h>
using namespace std;

int n;
vector<int> ans;
vector<int> qv;

int ask(const vector<int>& q) {
    cout << 0;
    for (int i = 1; i <= n; ++i) {
        cout << ' ' << q[i];
    }
    cout << endl;
    cout.flush();
    int x;
    if (!(cin >> x)) exit(0);
    return x;
}

void guess() {
    cout << 1;
    for (int i = 1; i <= n; ++i) {
        cout << ' ' << ans[i];
    }
    cout << endl;
    cout.flush();
    exit(0);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n)) return 0;
    ans.assign(n + 1, 0);
    qv.assign(n + 1, 1);

    if (n == 1) {
        ans[1] = 1;
        guess();
    }

    int L = 0;
    while ((1 << L) <= n) ++L;

    int knownCount = 0;
    mt19937 rng(712367821);

    for (int v = 1; v + 1 <= n; v += 2) {
        int w = v + 1;

        vector<int> U;
        for (int i = 1; i <= n; ++i)
            if (ans[i] == 0) U.push_back(i);
        if ((int)U.size() <= 1) break;

        int baseC = knownCount;
        vector<int> s(L);

        // Stage 1: get s[bit] from bit-based subsets
        for (int bit = 0; bit < L; ++bit) {
            for (int i = 1; i <= n; ++i) {
                if (ans[i] != 0) {
                    qv[i] = ans[i];
                } else {
                    if ((i >> bit) & 1) qv[i] = w;
                    else qv[i] = v;
                }
            }
            int r = ask(qv);
            int d = r - baseC; // 0..2
            s[bit] = d - 1;    // -1,0,1
        }

        // Stage 1: enumerate candidates
        vector<pair<int,int>> P;
        for (int idx = 0; idx < (int)U.size(); ++idx) {
            int a = U[idx];
            bool ok = true;
            for (int bit = 0; bit < L; ++bit) {
                int ba = (a >> bit) & 1;
                if (s[bit] == 1 && ba == 1) { ok = false; break; }
                if (s[bit] == -1 && ba == 0) { ok = false; break; }
            }
            if (!ok) continue;
            int b = a;
            for (int bit = 0; bit < L; ++bit) {
                if (s[bit] == 1) b |= (1 << bit);
                else if (s[bit] == -1) b &= ~(1 << bit);
            }
            if (b < 1 || b > n) continue;
            if (ans[b] != 0) continue;
            if (a == b) continue;
            P.emplace_back(a, b);
        }

        if (P.empty()) {
            // Should not happen; fall back trivially (invalid but avoids infinite loop)
            // Assign remaining unknown indices arbitrarily for safety.
            for (int i : U) {
                if (ans[i] == 0) ans[i] = v; // arbitrary
            }
            guess();
        }

        // Stage 2: reduce candidates with randomized subsets
        if (P.size() > 1) {
            while (P.size() > 1) {
                int K = (int)P.size();
                int SAMPLE = 25;
                int bestMax = K;
                vector<char> bestMem(n + 1, 0);
                vector<char> mem(n + 1, 0);

                for (int att = 0; att < SAMPLE; ++att) {
                    for (int j : U) {
                        mem[j] = (char)(rng() & 1);
                    }
                    int c0 = 0, c1 = 0, c2 = 0;
                    for (auto &pr : P) {
                        int a = pr.first, b = pr.second;
                        bool inA = mem[a], inB = mem[b];
                        if (inA && !inB) ++c0;
                        else if (!inA && inB) ++c2;
                        else ++c1;
                    }
                    int curMax = max(c0, max(c1, c2));
                    if (curMax < bestMax) {
                        bestMax = curMax;
                        bestMem = mem;
                        if (bestMax <= (K + 2) / 3) break;
                    }
                }

                if (bestMax == K) {
                    // Fallback: force at least one candidate in a different group
                    fill(bestMem.begin(), bestMem.end(), 0);
                    int a = P[0].first, b = P[0].second;
                    bestMem[a] = 1;
                    bestMem[b] = 0;
                }

                for (int i = 1; i <= n; ++i) {
                    if (ans[i] != 0) qv[i] = ans[i];
                    else qv[i] = bestMem[i] ? w : v;
                }
                int r = ask(qv);
                int d = r - baseC; // 0,1,2

                vector<pair<int,int>> newP;
                newP.reserve(bestMax);
                for (auto &pr : P) {
                    int a = pr.first, b = pr.second;
                    bool inA = bestMem[a], inB = bestMem[b];
                    int pred;
                    if (inA && !inB) pred = 0;
                    else if (!inA && inB) pred = 2;
                    else pred = 1;
                    if (pred == d) newP.push_back(pr);
                }
                if (newP.empty()) {
                    // Safety fallback: stop refining further
                    break;
                }
                P.swap(newP);
            }
        }

        pair<int,int> finalPair = P[0];
        int iv = finalPair.first;
        int iw = finalPair.second;
        ans[iv] = v;
        ans[iw] = w;
        knownCount += 2;
    }

    if (n % 2 == 1) {
        int lastVal = n;
        int idx = -1;
        for (int i = 1; i <= n; ++i) {
            if (ans[i] == 0) { idx = i; break; }
        }
        if (idx != -1) ans[idx] = lastVal;
    }

    guess();
    return 0;
}