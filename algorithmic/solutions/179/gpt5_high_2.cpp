#include <bits/stdc++.h>
#include <boost/multiprecision/cpp_int.hpp>

using namespace std;
using boost::multiprecision::cpp_int;

static std::mt19937_64 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count());

cpp_int parseBig(const string &s) {
    cpp_int x = 0;
    for (char c : s) {
        if (c >= '0' && c <= '9') {
            x *= 10;
            x += (c - '0');
        }
    }
    return x;
}

inline cpp_int absDiff(const cpp_int &a, const cpp_int &b) {
    return (a >= b) ? (a - b) : (b - a);
}

struct Candidate {
    vector<char> b;
    cpp_int S;
    Candidate() {}
    Candidate(int n) : b(n, 0), S(0) {}
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    string sW;
    if (!(cin >> n >> sW)) {
        return 0;
    }
    cpp_int W = parseBig(sW);
    vector<cpp_int> a(n);
    for (int i = 0; i < n; ++i) {
        string s;
        cin >> s;
        a[i] = parseBig(s);
    }

    auto consider = [&](const vector<char> &b, const cpp_int &S,
                        vector<char> &bestB, cpp_int &bestS, cpp_int &bestDiff, bool &hasBest) {
        cpp_int diff = absDiff(W, S);
        if (!hasBest) {
            bestB = b;
            bestS = S;
            bestDiff = diff;
            hasBest = true;
            return;
        }
        if (diff < bestDiff) {
            bestB = b;
            bestS = S;
            bestDiff = diff;
        } else if (diff == bestDiff) {
            bool sUnder = (S <= W);
            bool bestUnder = (bestS <= W);
            if (sUnder != bestUnder) {
                if (sUnder && !bestUnder) {
                    bestB = b;
                    bestS = S;
                    bestDiff = diff;
                }
            } else {
                // Both under or both over, tie-break: closer to W but prefer larger S if under, smaller S if over
                if (sUnder) {
                    if (S > bestS) {
                        bestB = b;
                        bestS = S;
                        bestDiff = diff;
                    }
                } else {
                    if (S < bestS) {
                        bestB = b;
                        bestS = S;
                        bestDiff = diff;
                    }
                }
            }
        }
    };

    // Initial trivial candidates
    vector<char> bestB(n, 0);
    cpp_int bestS = 0, bestDiff = 0;
    bool hasBest = false;

    // Empty set
    {
        vector<char> b(n, 0);
        consider(b, cpp_int(0), bestB, bestS, bestDiff, hasBest);
    }

    // All set
    {
        vector<char> b(n, 1);
        cpp_int S = 0;
        for (int i = 0; i < n; ++i) S += a[i];
        consider(b, S, bestB, bestS, bestDiff, hasBest);
    }

    // Best single item
    {
        int bestIdx = -1;
        cpp_int bestD;
        bool have = false;
        for (int i = 0; i < n; ++i) {
            cpp_int d = absDiff(W, a[i]);
            if (!have || d < bestD) {
                have = true;
                bestD = d;
                bestIdx = i;
            }
        }
        if (bestIdx >= 0) {
            vector<char> b(n, 0);
            b[bestIdx] = 1;
            consider(b, a[bestIdx], bestB, bestS, bestDiff, hasBest);
        }
    }

    // Best pair
    {
        vector<int> id(n);
        iota(id.begin(), id.end(), 0);
        sort(id.begin(), id.end(), [&](int i, int j){ return a[i] < a[j]; });
        int l = 0, r = n - 1;
        cpp_int bestPairDiff;
        bool have = false;
        int bi = -1, bj = -1;
        while (l < r) {
            cpp_int sum = a[id[l]] + a[id[r]];
            cpp_int d = absDiff(W, sum);
            if (!have || d < bestPairDiff) {
                have = true;
                bestPairDiff = d;
                bi = id[l];
                bj = id[r];
            }
            if (sum < W) {
                ++l;
            } else if (sum > W) {
                --r;
            } else {
                // exact
                bi = id[l];
                bj = id[r];
                break;
            }
        }
        if (bi >= 0 && bj >= 0) {
            vector<char> b(n, 0);
            b[bi] = 1; b[bj] = 1;
            cpp_int S = a[bi] + a[bj];
            consider(b, S, bestB, bestS, bestDiff, hasBest);
        }
    }

    // Helper lambdas: greedy under, greedy over
    auto greedy_under = [&](const vector<int> &order) -> Candidate {
        Candidate cand(n);
        cpp_int L = W; // remaining capacity
        for (int idx : order) {
            const cpp_int &w = a[idx];
            if (w <= L) {
                cand.b[idx] = 1;
                L -= w;
            }
        }
        cand.S = W - L;
        return cand;
    };

    auto greedy_over = [&](const vector<int> &order, bool &ok) -> Candidate {
        Candidate cand(n);
        cpp_int S = 0;
        ok = false;
        for (int idx : order) {
            cand.b[idx] = 1;
            S += a[idx];
            if (S >= W) {
                ok = true;
                break;
            }
        }
        if (!ok) {
            // didn't reach W
            return cand;
        }
        // prune: remove largest chosen items if possible
        vector<int> chosen;
        chosen.reserve(n);
        for (int i = 0; i < n; ++i) if (cand.b[i]) chosen.push_back(i);
        sort(chosen.begin(), chosen.end(), [&](int i, int j){ return a[i] > a[j]; });
        for (int idx : chosen) {
            const cpp_int &w = a[idx];
            if (S >= w && (S - w) >= W) {
                cand.b[idx] = 0;
                S -= w;
            }
        }
        cand.S = S;
        return cand;
    };

    // Create standard orders
    vector<int> idAsc(n), idDesc(n);
    iota(idAsc.begin(), idAsc.end(), 0);
    iota(idDesc.begin(), idDesc.end(), 0);
    sort(idAsc.begin(), idAsc.end(), [&](int i, int j){ return a[i] < a[j]; });
    sort(idDesc.begin(), idDesc.end(), [&](int i, int j){ return a[i] > a[j]; });

    // Greedy under: asc, desc, random tries
    Candidate bestUnderCand(n);
    cpp_int bestUnderDiff;
    bool haveUnder = false;

    auto considerUnderCand = [&](const Candidate &c) {
        cpp_int diff = absDiff(W, c.S);
        if (!haveUnder || diff < bestUnderDiff) {
            bestUnderDiff = diff;
            bestUnderCand = c;
            haveUnder = true;
        }
    };

    considerUnderCand(greedy_under(idDesc));
    considerUnderCand(greedy_under(idAsc));

    int RAND_UNDER_TRIES = 16;
    for (int t = 0; t < RAND_UNDER_TRIES; ++t) {
        vector<int> order(n);
        iota(order.begin(), order.end(), 0);
        shuffle(order.begin(), order.end(), rng);
        considerUnderCand(greedy_under(order));
    }

    // Greedy over: asc, desc, random tries
    Candidate bestOverCand(n);
    cpp_int bestOverDiff;
    bool haveOver = false;

    auto considerOverCand = [&](const Candidate &c) {
        cpp_int diff = absDiff(W, c.S);
        if (!haveOver || diff < bestOverDiff) {
            bestOverDiff = diff;
            bestOverCand = c;
            haveOver = true;
        }
    };

    {
        bool ok = false;
        Candidate c = greedy_over(idAsc, ok);
        if (ok) considerOverCand(c);
    }
    {
        bool ok = false;
        Candidate c = greedy_over(idDesc, ok);
        if (ok) considerOverCand(c);
    }
    int RAND_OVER_TRIES = 16;
    for (int t = 0; t < RAND_OVER_TRIES; ++t) {
        vector<int> order(n);
        iota(order.begin(), order.end(), 0);
        shuffle(order.begin(), order.end(), rng);
        bool ok = false;
        Candidate c = greedy_over(order, ok);
        if (ok) considerOverCand(c);
    }

    // Consider these greedy results
    if (haveUnder) consider(bestUnderCand.b, bestUnderCand.S, bestB, bestS, bestDiff, hasBest);
    if (haveOver) consider(bestOverCand.b, bestOverCand.S, bestB, bestS, bestDiff, hasBest);

    // Improvement for under (only on the best under candidate)
    if (haveUnder) {
        vector<char> b = bestUnderCand.b;
        cpp_int S = bestUnderCand.S;
        cpp_int L = W - S;

        auto packAdd = [&](vector<char> &bref, cpp_int &Lref) {
            bool any = false;
            while (true) {
                int bestIdx = -1;
                cpp_int bestVal = 0;
                bool found = false;
                for (int i = 0; i < n; ++i) if (!bref[i]) {
                    const cpp_int &w = a[i];
                    if (w <= Lref) {
                        if (!found || w > bestVal) {
                            found = true;
                            bestVal = w;
                            bestIdx = i;
                        }
                    }
                }
                if (found && bestIdx >= 0) {
                    bref[bestIdx] = 1;
                    Lref -= bestVal;
                    any = true;
                } else {
                    break;
                }
            }
            return any;
        };

        // 1-1 swap improvements
        int MAX_11_LOOPS = 3;
        for (int loop = 0; loop < MAX_11_LOOPS; ++loop) {
            bool improved = false;
            // Build lists
            vector<int> chosen, notchosen;
            chosen.reserve(n);
            notchosen.reserve(n);
            for (int i = 0; i < n; ++i) {
                if (b[i]) chosen.push_back(i);
                else notchosen.push_back(i);
            }
            // Find best 1-1 swap
            bool found = false;
            int bi = -1, bj = -1;
            cpp_int bestDelta = 0; // ai - aj
            for (int ii : notchosen) {
                const cpp_int &wi = a[ii];
                for (int jj : chosen) {
                    const cpp_int &wj = a[jj];
                    if (wi > wj) {
                        cpp_int delta = wi - wj;
                        if (delta <= L) {
                            if (!found || delta > bestDelta) {
                                found = true;
                                bestDelta = delta;
                                bi = ii; bj = jj;
                            }
                        }
                    }
                }
            }
            if (found && bi >= 0 && bj >= 0) {
                b[bi] = 1;
                b[bj] = 0;
                L -= bestDelta;
                improved = true;
                packAdd(b, L);
            }
            if (!improved) break;
        }

        // 1->2 swap improvements (sampled)
        int MAX_12_LOOPS = 2;
        const int SAMPLE_NOTCHOSEN_MAX = 200;
        const int SAMPLE_CHOSEN_MAX = 100;

        for (int loop = 0; loop < MAX_12_LOOPS; ++loop) {
            // Build lists
            vector<int> chosen, notchosen;
            for (int i = 0; i < n; ++i) {
                if (b[i]) chosen.push_back(i);
                else notchosen.push_back(i);
            }
            if ((int)notchosen.size() < 2 || chosen.empty()) break;

            // sort chosen by value desc, take top T
            sort(chosen.begin(), chosen.end(), [&](int i, int j){ return a[i] > a[j]; });
            if ((int)chosen.size() > SAMPLE_CHOSEN_MAX) chosen.resize(SAMPLE_CHOSEN_MAX);

            // sort notchosen by value desc, take top K
            sort(notchosen.begin(), notchosen.end(), [&](int i, int j){ return a[i] > a[j]; });
            if ((int)notchosen.size() > SAMPLE_NOTCHOSEN_MAX) notchosen.resize(SAMPLE_NOTCHOSEN_MAX);
            // build ascending for two-pointer
            vector<int> ncAsc = notchosen;
            sort(ncAsc.begin(), ncAsc.end(), [&](int i, int j){ return a[i] < a[j]; });

            bool improved = false;
            int best_j = -1, best_i1 = -1, best_i2 = -1;
            cpp_int best_gain = 0; // sumPair - aj
            cpp_int bestPairSum = 0;

            for (int jidx : chosen) {
                const cpp_int &wj = a[jidx];
                cpp_int cap = L + wj;
                int l = 0, r = (int)ncAsc.size() - 1;
                cpp_int bestSum = -1;
                int bi1 = -1, bi2 = -1;
                while (l < r) {
                    const cpp_int &wl = a[ncAsc[l]];
                    const cpp_int &wr = a[ncAsc[r]];
                    cpp_int s = wl + wr;
                    if (s <= cap) {
                        if (bestSum < 0 || s > bestSum) {
                            bestSum = s;
                            bi1 = ncAsc[l];
                            bi2 = ncAsc[r];
                        }
                        ++l;
                    } else {
                        --r;
                    }
                }
                if (bestSum >= 0 && bestSum > wj) {
                    cpp_int gain = bestSum - wj;
                    if (!improved || gain > best_gain) {
                        improved = true;
                        best_gain = gain;
                        best_j = jidx;
                        best_i1 = bi1;
                        best_i2 = bi2;
                        bestPairSum = bestSum;
                    }
                }
            }

            if (improved) {
                b[best_j] = 0;
                b[best_i1] = 1;
                b[best_i2] = 1;
                // update L: new leftover = (L + aj) - pairSum
                L = (L + a[best_j]) - bestPairSum;
                // pack additions
                packAdd(b, L);
            } else {
                break;
            }
        }

        cpp_int improvedS = W - L;
        consider(b, improvedS, bestB, bestS, bestDiff, hasBest);
    }

    // Also consider pruned overshoot best (already considered)

    // Output bestB
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (bestB[i] ? 1 : 0);
    }
    cout << '\n';

    return 0;
}