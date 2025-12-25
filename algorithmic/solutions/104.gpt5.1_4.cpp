#include <bits/stdc++.h>
using namespace std;

const int MAXN = 100000 + 5;

bool alive_[MAXN];
unsigned char lastBit_[MAXN];
unsigned char runLen_[MAXN];

int delta0[MAXN], delta1[MAXN];
int pref0[MAXN], pref1[MAXN];

void precomputeY(int Y, int n, int *delta, int *pref, int &base) {
    base = 0;
    pref[0] = 0;
    for (int i = 1; i <= n; ++i) {
        if (!alive_[i]) {
            delta[i] = 0;
            pref[i] = pref[i - 1];
            continue;
        }
        int len = runLen_[i];

        int newH_out = Y;
        bool survive_out;
        if (len == 0) survive_out = true;
        else if (newH_out == (int)lastBit_[i]) survive_out = (len < 2);
        else survive_out = true;
        int aOut = survive_out ? 1 : 0;
        base += aOut;

        int newH_in = Y ^ 1;
        bool survive_in;
        if (len == 0) survive_in = true;
        else if (newH_in == (int)lastBit_[i]) survive_in = (len < 2);
        else survive_in = true;
        int bIn = survive_in ? 1 : 0;

        delta[i] = bIn - aOut; // in {-1,0,1}
        pref[i] = pref[i - 1] + delta[i];
    }
}

tuple<int,int,long long> bestIntervalKadane(int n, const int *delta) {
    long long bestSum = (long long)4e18;
    long long curSum = 0;
    int bestL = 1, bestR = 1, s = 1;
    for (int i = 1; i <= n; ++i) {
        curSum += delta[i];
        if (curSum < bestSum) {
            bestSum = curSum;
            bestL = s;
            bestR = i;
        }
        if (curSum > 0) {
            curSum = 0;
            s = i + 1;
        }
    }
    return {bestL, bestR, bestSum};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        cin >> n;

        for (int i = 1; i <= n; ++i) {
            alive_[i] = true;
            lastBit_[i] = 0;
            runLen_[i] = 0;
        }
        int countAlive = n;

        long double logN = logl((long double)n);
        long double logB = logl((long double)1.116L);
        int limitQ = (int)ceill(logN / logB) * 2;

        int queriesUsed = 0;

        while (countAlive > 2 && queriesUsed < limitQ) {
            int base0, base1;
            precomputeY(0, n, delta0, pref0, base0);
            precomputeY(1, n, delta1, pref1, base1);

            int l = 1, r = n;

            if (countAlive <= 40) {
                vector<int> pos;
                pos.reserve(countAlive);
                for (int i = 1; i <= n; ++i)
                    if (alive_[i]) pos.push_back(i);
                long long bestWorst = (long long)4e18;
                int bestL = pos[0], bestR = pos[0];
                for (int i = 0; i < (int)pos.size(); ++i) {
                    for (int j = i; j < (int)pos.size(); ++j) {
                        int L = pos[i], R = pos[j];
                        long long val0 = (long long)base0 + (pref0[R] - pref0[L - 1]);
                        long long val1 = (long long)base1 + (pref1[R] - pref1[L - 1]);
                        long long w = (val0 > val1) ? val0 : val1;
                        if (w < bestWorst) {
                            bestWorst = w;
                            bestL = L;
                            bestR = R;
                        }
                    }
                }
                l = bestL;
                r = bestR;
            } else {
                int L0, R0, L1, R1;
                long long sum0, sum1;
                tie(L0, R0, sum0) = bestIntervalKadane(n, delta0);
                tie(L1, R1, sum1) = bestIntervalKadane(n, delta1);

                long long val0_0 = (long long)base0 + (pref0[R0] - pref0[L0 - 1]);
                long long val0_1 = (long long)base1 + (pref1[R0] - pref1[L0 - 1]);
                long long worst0 = (val0_0 > val0_1) ? val0_0 : val0_1;

                long long val1_0 = (long long)base0 + (pref0[R1] - pref0[L1 - 1]);
                long long val1_1 = (long long)base1 + (pref1[R1] - pref1[L1 - 1]);
                long long worst1 = (val1_0 > val1_1) ? val1_0 : val1_1;

                if (worst0 < worst1) {
                    l = L0;
                    r = R0;
                } else {
                    l = L1;
                    r = R1;
                }

                bool hasAlive = false;
                for (int i = l; i <= r && !hasAlive; ++i) {
                    if (alive_[i]) hasAlive = true;
                }
                if (!hasAlive) {
                    int id = -1;
                    int left = l;
                    while (left >= 1 && id == -1) {
                        if (alive_[left]) id = left;
                        --left;
                    }
                    int right = r;
                    while (right <= n && id == -1) {
                        if (alive_[right]) id = right;
                        ++right;
                    }
                    if (id == -1) {
                        for (int i = 1; i <= n; ++i) {
                            if (alive_[i]) {
                                id = i;
                                break;
                            }
                        }
                    }
                    l = r = (id == -1 ? 1 : id);
                }
            }

            cout << "? " << l << " " << r << '\n';
            cout.flush();
            ++queriesUsed;

            int x;
            if (!(cin >> x)) return 0;
            int lenSeg = r - l + 1;
            int Y = (x == lenSeg) ? 1 : 0;

            for (int i = 1; i <= n; ++i) {
                if (!alive_[i]) continue;
                int A = (l <= i && i <= r) ? 1 : 0;
                int newH = A ^ Y;
                unsigned char lenPrev = runLen_[i];
                if (lenPrev == 0) {
                    lastBit_[i] = (unsigned char)newH;
                    runLen_[i] = 1;
                } else {
                    if (newH == (int)lastBit_[i]) {
                        if (lenPrev == 2) {
                            alive_[i] = false;
                            runLen_[i] = 0;
                            --countAlive;
                        } else {
                            runLen_[i] = 2;
                        }
                    } else {
                        lastBit_[i] = (unsigned char)newH;
                        runLen_[i] = 1;
                    }
                }
            }
        }

        vector<int> cand;
        cand.reserve(countAlive);
        for (int i = 1; i <= n; ++i)
            if (alive_[i]) cand.push_back(i);
        if (cand.empty()) cand.push_back(1);

        auto guess = [&](int a) -> int {
            cout << "! " << a << '\n';
            cout.flush();
            int y;
            if (!(cin >> y)) y = 0;
            return y;
        };

        if (cand.size() == 1) {
            guess(cand[0]);
            cout << "#\n";
            cout.flush();
        } else {
            int first = cand[0];
            int res1 = guess(first);
            if (res1 == 1) {
                cout << "#\n";
                cout.flush();
            } else {
                int second = (cand.size() >= 2 ? cand[1] : (first == 1 ? 2 : 1));
                guess(second);
                cout << "#\n";
                cout.flush();
            }
        }
    }

    return 0;
}