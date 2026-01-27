#include <bits/stdc++.h>
using namespace std;

struct Item {
    string name;
    long long q, v, m, l;
};

static const long long CAP_M = 20000000LL;
static const long long CAP_L = 25000000LL;

struct Solution {
    vector<long long> x;
    long long val;
    long long usedM;
    long long usedL;
    Solution() {}
    Solution(int n): x(n,0), val(0), usedM(0), usedL(0) {}
};

static inline long long addable(const Item& it, long long remM, long long remL, long long have, long long q) {
    if (it.m == 0 || it.l == 0) return 0;
    long long byM = remM / it.m;
    long long byL = remL / it.l;
    long long can = min({q - have, byM, byL});
    if (can < 0) can = 0;
    return can;
}

static Solution evaluate_solution(const vector<Item>& items, const vector<long long>& x) {
    Solution s;
    s.x = x;
    s.val = 0;
    s.usedM = 0;
    s.usedL = 0;
    for (size_t i = 0; i < items.size(); ++i) {
        s.val += x[i] * items[i].v;
        s.usedM += x[i] * items[i].m;
        s.usedL += x[i] * items[i].l;
    }
    return s;
}

static inline long double ratio_comb(const Item& it, long double a, long double b) {
    long double denom = a * (long double)it.m + b * (long double)it.l;
    if (denom <= 0) return (long double)0;
    return (long double)it.v / denom;
}

static Solution pack_by_ratio(const vector<Item>& items, long double a, long double b) {
    int n = (int)items.size();
    vector<int> ord(n);
    iota(ord.begin(), ord.end(), 0);
    sort(ord.begin(), ord.end(), [&](int i, int j){
        long double ri = ratio_comb(items[i], a, b);
        long double rj = ratio_comb(items[j], a, b);
        if (ri != rj) return ri > rj;
        if (items[i].v != items[j].v) return items[i].v > items[j].v;
        return i < j;
    });
    vector<long long> x(n,0);
    long long remM = CAP_M, remL = CAP_L;
    for (int idx : ord) {
        long long can = addable(items[idx], remM, remL, x[idx], items[idx].q);
        if (can > 0) {
            x[idx] += can;
            remM -= can * items[idx].m;
            remL -= can * items[idx].l;
        }
    }
    return evaluate_solution(items, x);
}

static Solution pack_dynamic(const vector<Item>& items, bool addAll, int stepCap = 50, long long maxIter = 5000) {
    int n = (int)items.size();
    vector<long long> x(n,0);
    long long remM = CAP_M, remL = CAP_L;
    long long iters = 0;
    while (iters++ < maxIter) {
        int best = -1;
        long double bestScore = -1;
        for (int i = 0; i < n; ++i) {
            if (x[i] >= items[i].q) continue;
            if (items[i].m > remM || items[i].l > remL) continue;
            long double score = (long double)items[i].v / ((long double)items[i].m / (remM + 1.0L) + (long double)items[i].l / (remL + 1.0L));
            if (score > bestScore) {
                bestScore = score;
                best = i;
            }
        }
        if (best == -1) break;
        long long kmax = addable(items[best], remM, remL, x[best], items[best].q);
        if (kmax <= 0) break;
        long long k = addAll ? kmax : min<long long>(kmax, stepCap);
        x[best] += k;
        remM -= k * items[best].m;
        remL -= k * items[best].l;
    }
    return evaluate_solution(items, x);
}

static void repair_feasible(const vector<Item>& items, vector<long long>& x, long long& usedM, long long& usedL, long long& val) {
    // Remove items until within both capacities, preferring to remove the least "efficient" for the most exceeded constraint
    int n = (int)items.size();
    while (usedM > CAP_M || usedL > CAP_L) {
        bool massEx = usedM > CAP_M;
        long double overM = massEx ? (long double)(usedM - CAP_M) / CAP_M : 0.0L;
        long double overL = (usedL > CAP_L) ? (long double)(usedL - CAP_L) / CAP_L : 0.0L;
        bool focusMass = overM >= overL;
        int removeIdx = -1;
        long double bestMetric = 1e100L;
        for (int i = 0; i < n; ++i) {
            if (x[i] <= 0) continue;
            long double denom = focusMass ? (long double)items[i].m : (long double)items[i].l;
            if (denom <= 0) denom = 1.0L;
            long double metric = (long double)items[i].v / denom; // remove smallest value per unit of the exceeding resource
            if (metric < bestMetric) {
                bestMetric = metric;
                removeIdx = i;
            }
        }
        if (removeIdx == -1) break; // nothing to remove
        x[removeIdx] -= 1;
        usedM -= items[removeIdx].m;
        usedL -= items[removeIdx].l;
        val -= items[removeIdx].v;
    }
}

static void improve_fill(const vector<Item>& items, vector<long long>& x, long long& usedM, long long& usedL, long long& val, int stepCap = 50, long long maxIter = 2000) {
    long long remM = CAP_M - usedM;
    long long remL = CAP_L - usedL;
    int n = (int)items.size();
    long long iters = 0;
    while (iters++ < maxIter) {
        int best = -1;
        long double bestScore = -1;
        for (int i = 0; i < n; ++i) {
            if (x[i] >= items[i].q) continue;
            if (items[i].m > remM || items[i].l > remL) continue;
            long double score = (long double)items[i].v / ((long double)items[i].m / (remM + 1.0L) + (long double)items[i].l / (remL + 1.0L));
            if (score > bestScore) {
                bestScore = score;
                best = i;
            }
        }
        if (best == -1) break;
        long long kmax = addable(items[best], remM, remL, x[best], items[best].q);
        if (kmax <= 0) break;
        long long k = min<long long>(kmax, stepCap);
        x[best] += k;
        long long dm = k * items[best].m;
        long long dl = k * items[best].l;
        usedM += dm; usedL += dl; val += k * items[best].v;
        remM -= dm; remL -= dl;
    }
}

static void swap_improvement(const vector<Item>& items, vector<long long>& x, long long& usedM, long long& usedL, long long& val, int rmax = 3, int maxIters = 100) {
    int n = (int)items.size();
    for (int iter = 0; iter < maxIters; ++iter) {
        long long remM = CAP_M - usedM;
        long long remL = CAP_L - usedL;
        long long bestDelta = 0;
        int bestI = -1, bestJ = -1, bestR = 0, bestT = 0;
        for (int i = 0; i < n; ++i) if (x[i] > 0) {
            int rlim = (int)min<long long>(rmax, x[i]);
            for (int r = 1; r <= rlim; ++r) {
                long long freeM = remM + r * items[i].m;
                long long freeL = remL + r * items[i].l;
                for (int j = 0; j < n; ++j) {
                    if (j == i && items[j].q == x[j]) continue;
                    long long canAdd = 0;
                    if (items[j].m > 0 && items[j].l > 0) {
                        canAdd = min({ items[j].q - x[j], freeM / items[j].m, freeL / items[j].l });
                    }
                    if (canAdd <= 0) continue;
                    long long delta = canAdd * items[j].v - r * items[i].v;
                    if (delta > bestDelta) {
                        bestDelta = delta;
                        bestI = i; bestJ = j; bestR = r; bestT = (int)canAdd;
                    }
                }
            }
        }
        if (bestDelta > 0 && bestI != -1) {
            x[bestI] -= bestR;
            usedM -= bestR * items[bestI].m;
            usedL -= bestR * items[bestI].l;
            val  -= bestR * items[bestI].v;
            long long remM2 = CAP_M - usedM;
            long long remL2 = CAP_L - usedL;
            long long canAdd = min({ items[bestJ].q - x[bestJ], remM2 / items[bestJ].m, remL2 / items[bestJ].l });
            if (canAdd > bestT) canAdd = bestT;
            if (canAdd > 0) {
                x[bestJ] += canAdd;
                usedM += canAdd * items[bestJ].m;
                usedL += canAdd * items[bestJ].l;
                val  += canAdd * items[bestJ].v;
            }
        } else {
            break;
        }
    }
}

static void multi_swap_improvement(const vector<Item>& items, vector<long long>& x, long long& usedM, long long& usedL, long long& val, int rmax = 2, int maxIters = 20) {
    int n = (int)items.size();
    for (int iter = 0; iter < maxIters; ++iter) {
        long long remM = CAP_M - usedM;
        long long remL = CAP_L - usedL;
        long long bestDelta = 0;
        int bi1=-1, bi2=-1, bj=-1, br1=0, br2=0, bt=0;
        for (int i1 = 0; i1 < n; ++i1) if (x[i1] > 0) {
            int r1lim = (int)min<long long>(rmax, x[i1]);
            for (int r1 = 0; r1 <= r1lim; ++r1) {
                if (r1 == 0 && rmax > 0) continue; // ensure at least one removal overall; will be handled by i2 loop
                long long freeM1 = remM + r1 * items[i1].m;
                long long freeL1 = remL + r1 * items[i1].l;
                for (int i2 = 0; i2 < n; ++i2) if (x[i2] > 0 && (i2 != i1 || x[i1] - r1 > 0)) {
                    int r2lim = (int)min<long long>(rmax, x[i2] - (i2==i1 ? r1 : 0));
                    for (int r2 = 0; r2 <= r2lim; ++r2) {
                        if (r1 == 0 && r2 == 0) continue;
                        long long freeM = freeM1 + r2 * items[i2].m;
                        long long freeL = freeL1 + r2 * items[i2].l;
                        for (int j = 0; j < n; ++j) {
                            if (items[j].m <= 0 || items[j].l <= 0) continue;
                            long long canAdd = min({ items[j].q - x[j], freeM / items[j].m, freeL / items[j].l });
                            if (canAdd <= 0) continue;
                            long long delta = canAdd * items[j].v - r1 * items[i1].v - r2 * items[i2].v;
                            if (delta > bestDelta) {
                                bestDelta = delta;
                                bi1=i1; bi2=i2; bj=j; br1=r1; br2=r2; bt=(int)canAdd;
                            }
                        }
                    }
                }
            }
        }
        if (bestDelta > 0 && bj != -1) {
            if (br1 > 0) {
                x[bi1] -= br1;
                usedM -= br1 * items[bi1].m;
                usedL -= br1 * items[bi1].l;
                val  -= br1 * items[bi1].v;
            }
            if (br2 > 0) {
                x[bi2] -= br2;
                usedM -= br2 * items[bi2].m;
                usedL -= br2 * items[bi2].l;
                val  -= br2 * items[bi2].v;
            }
            long long remM2 = CAP_M - usedM;
            long long remL2 = CAP_L - usedL;
            long long canAdd = min({ items[bj].q - x[bj], remM2 / items[bj].m, remL2 / items[bj].l });
            if (canAdd > bt) canAdd = bt;
            if (canAdd > 0) {
                x[bj] += canAdd;
                usedM += canAdd * items[bj].m;
                usedL += canAdd * items[bj].l;
                val  += canAdd * items[bj].v;
            }
        } else {
            break;
        }
    }
}

// Parse simple JSON format as per problem
static vector<Item> parse_input() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    string input((istreambuf_iterator<char>(cin)), istreambuf_iterator<char>());
    vector<Item> items;
    size_t pos = 0;
    while (true) {
        size_t q1 = input.find('"', pos);
        if (q1 == string::npos) break;
        size_t q2 = input.find('"', q1 + 1);
        if (q2 == string::npos) break;
        string name = input.substr(q1 + 1, q2 - q1 - 1);
        pos = q2 + 1;
        size_t lb = input.find('[', pos);
        if (lb == string::npos) break;
        size_t rb = input.find(']', lb + 1);
        if (rb == string::npos) break;
        string arr = input.substr(lb + 1, rb - lb - 1);
        pos = rb + 1;
        // Extract integers from arr
        vector<long long> nums;
        long long sign = 1, val = 0;
        bool inNum = false, neg = false;
        for (size_t i = 0; i < arr.size(); ++i) {
            char c = arr[i];
            if ((c >= '0' && c <= '9') || (c == '-' && !inNum)) {
                if (!inNum) {
                    inNum = true;
                    val = 0;
                    neg = (c == '-');
                    if (!neg && (c >= '0' && c <= '9')) {
                        val = c - '0';
                    }
                } else {
                    if (c == '-') { /* ignore */ }
                    else val = val * 10 + (c - '0');
                }
            } else {
                if (inNum) {
                    nums.push_back(neg ? -val : val);
                    inNum = false;
                }
            }
        }
        if (inNum) {
            nums.push_back(neg ? -val : val);
        }
        if (nums.size() >= 4) {
            Item it;
            it.name = name;
            it.q = nums[0];
            it.v = nums[1];
            it.m = nums[2];
            it.l = nums[3];
            items.push_back(it);
        }
    }
    return items;
}

int main() {
    auto items = parse_input();
    int n = (int)items.size();
    if (n == 0) {
        // Output empty JSON
        cout << "{\n}\n";
        return 0;
    }

    auto start = chrono::steady_clock::now();
    auto time_limit = chrono::milliseconds(950);

    Solution best(n);
    best.val = -1;

    // Candidate heuristics
    vector<pair<long double,long double>> coeffs;
    // deterministic ones
    coeffs.emplace_back(1.0L / CAP_M, 1.0L / CAP_L);
    coeffs.emplace_back(1.0L / CAP_M, 0.0L);
    coeffs.emplace_back(0.0L, 1.0L / CAP_L);
    // Balanced by max usage
    coeffs.emplace_back(1.0L / CAP_M, 1.0L / CAP_L);
    // Various alpha
    vector<long double> alphas = {0.25L, 0.4L, 0.6L, 0.75L};
    for (auto a : alphas) {
        coeffs.emplace_back(a / CAP_M, (1.0L - a) / CAP_L);
    }

    // Run deterministic packings
    for (auto [a,b] : coeffs) {
        Solution s = pack_by_ratio(items, a, b);
        long long usedM = s.usedM, usedL = s.usedL, val = s.val;
        vector<long long> x = s.x;
        // Repair if needed
        if (usedM > CAP_M || usedL > CAP_L) {
            repair_feasible(items, x, usedM, usedL, val);
        }
        // Fill and improve
        improve_fill(items, x, usedM, usedL, val);
        swap_improvement(items, x, usedM, usedL, val);
        multi_swap_improvement(items, x, usedM, usedL, val);
        if (val > best.val) {
            best.x = x; best.val = val; best.usedM = usedM; best.usedL = usedL;
        }
    }

    // Dynamic greedy variants
    {
        Solution s1 = pack_dynamic(items, false, 50, 3000);
        long long usedM = s1.usedM, usedL = s1.usedL, val = s1.val;
        vector<long long> x = s1.x;
        if (usedM > CAP_M || usedL > CAP_L) {
            repair_feasible(items, x, usedM, usedL, val);
        }
        improve_fill(items, x, usedM, usedL, val);
        swap_improvement(items, x, usedM, usedL, val);
        multi_swap_improvement(items, x, usedM, usedL, val);
        if (val > best.val) {
            best.x = x; best.val = val; best.usedM = usedM; best.usedL = usedL;
        }
    }
    {
        Solution s2 = pack_dynamic(items, true, 50, 1000);
        long long usedM = s2.usedM, usedL = s2.usedL, val = s2.val;
        vector<long long> x = s2.x;
        if (usedM > CAP_M || usedL > CAP_L) {
            repair_feasible(items, x, usedM, usedL, val);
        }
        improve_fill(items, x, usedM, usedL, val);
        swap_improvement(items, x, usedM, usedL, val);
        multi_swap_improvement(items, x, usedM, usedL, val);
        if (val > best.val) {
            best.x = x; best.val = val; best.usedM = usedM; best.usedL = usedL;
        }
    }

    // Fractional rounding candidate using combined weight
    {
        vector<int> ord(n);
        iota(ord.begin(), ord.end(), 0);
        vector<long double> w(n);
        for (int i = 0; i < n; ++i) {
            w[i] = (long double)items[i].m / CAP_M + (long double)items[i].l / CAP_L;
            if (w[i] <= 0) w[i] = 1e-18L;
        }
        sort(ord.begin(), ord.end(), [&](int i, int j){
            long double ri = (long double)items[i].v / w[i];
            long double rj = (long double)items[j].v / w[j];
            if (ri != rj) return ri > rj;
            return i < j;
        });
        vector<long long> x(n,0);
        long double wcap = 2.0L;
        for (int id : ord) {
            if (wcap <= 0) break;
            long double maxFull = floor(wcap / w[id]);
            if (maxFull < 0) maxFull = 0;
            long long take = (long long)min<long double>((long double)items[id].q, maxFull);
            if (take > 0) {
                x[id] += take;
                wcap -= (long double)take * w[id];
            }
        }
        Solution s = evaluate_solution(items, x);
        long long usedM = s.usedM, usedL = s.usedL, val = s.val;
        if (usedM > CAP_M || usedL > CAP_L) {
            repair_feasible(items, x, usedM, usedL, val);
        }
        improve_fill(items, x, usedM, usedL, val);
        swap_improvement(items, x, usedM, usedL, val);
        multi_swap_improvement(items, x, usedM, usedL, val);
        if (val > best.val) {
            best.x = x; best.val = val; best.usedM = usedM; best.usedL = usedL;
        }
    }

    // Randomized attempts until time
    std::mt19937_64 rng(1234567);
    while (chrono::steady_clock::now() - start < time_limit) {
        long double a = (rng() % 10001) / 10000.0L; // [0,1]
        long double alpha = 0.2L + 0.6L * a; // [0.2,0.8]
        long double A = alpha / CAP_M;
        long double B = (1.0L - alpha) / CAP_L;
        Solution s = pack_by_ratio(items, A, B);
        long long usedM = s.usedM, usedL = s.usedL, val = s.val;
        vector<long long> x = s.x;
        if (usedM > CAP_M || usedL > CAP_L) {
            repair_feasible(items, x, usedM, usedL, val);
        }
        improve_fill(items, x, usedM, usedL, val);
        swap_improvement(items, x, usedM, usedL, val, 3, 20);
        multi_swap_improvement(items, x, usedM, usedL, val, 2, 5);
        if (val > best.val) {
            best.x = x; best.val = val; best.usedM = usedM; best.usedL = usedL;
        }
        if (chrono::steady_clock::now() - start > time_limit) break;
    }

    // Final feasibility check and small repair if needed
    {
        long long usedM = 0, usedL = 0, val = 0;
        for (int i = 0; i < n; ++i) {
            best.x[i] = max(0LL, min(best.x[i], items[i].q));
            usedM += best.x[i] * items[i].m;
            usedL += best.x[i] * items[i].l;
            val   += best.x[i] * items[i].v;
        }
        if (usedM > CAP_M || usedL > CAP_L) {
            repair_feasible(items, best.x, usedM, usedL, val);
        }
        best.usedM = usedM; best.usedL = usedL; best.val = val;
    }

    // Output JSON
    cout << "{\n";
    for (int i = 0; i < n; ++i) {
        cout << " \"" << items[i].name << "\": " << best.x[i];
        if (i + 1 < n) cout << ",\n";
        else cout << "\n";
    }
    cout << "}\n";
    return 0;
}