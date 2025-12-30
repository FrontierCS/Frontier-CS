#include <bits/stdc++.h>
using namespace std;

struct Type {
    string name;
    long long q;
    long long v;
    long long m;
    long long l;
};

struct PItem {
    int type;
    int mult;
    long long val;
    int wM;
    int wL;
};

static const long long MASS_CAP = 20000000LL;   // mg
static const long long VOL_CAP  = 25000000LL;   // uL

// Simple JSON-like parser tailored for the given input format
vector<Type> parseInput(istream& in) {
    string s((istreambuf_iterator<char>(in)), istreambuf_iterator<char>());
    vector<Type> items;
    size_t i = 0, n = s.size();

    auto skip_ws = [&]() {
        while (i < n && isspace((unsigned char)s[i])) i++;
    };
    auto skip_until = [&](char c){
        while (i < n && s[i] != c) i++;
        if (i < n && s[i] == c) i++;
    };
    auto parse_string = [&]() -> string {
        skip_ws();
        while (i < n && s[i] != '"') i++;
        if (i < n && s[i] == '"') i++;
        string res;
        while (i < n && s[i] != '"') {
            if (s[i] == '\\' && i + 1 < n) {
                res.push_back(s[i+1]);
                i += 2;
            } else {
                res.push_back(s[i++]);
            }
        }
        if (i < n && s[i] == '"') i++;
        return res;
    };
    auto parse_ll = [&]() -> long long {
        skip_ws();
        // move to first digit or '-'
        while (i < n && !(s[i] == '-' || (s[i] >= '0' && s[i] <= '9'))) i++;
        long long sign = 1;
        if (i < n && s[i] == '-') { sign = -1; i++; }
        long long val = 0;
        while (i < n && s[i] >= '0' && s[i] <= '9') {
            val = val * 10 + (s[i] - '0');
            i++;
        }
        return sign * val;
    };

    skip_ws();
    // expect {
    while (i < n && s[i] != '{') i++;
    if (i < n && s[i] == '{') i++;

    while (true) {
        skip_ws();
        if (i >= n) break;
        if (s[i] == '}') { i++; break; }
        string key = parse_string();
        skip_ws();
        // skip to '['
        while (i < n && s[i] != '[') i++;
        if (i < n && s[i] == '[') i++;
        long long q = parse_ll();
        long long v = parse_ll();
        long long m = parse_ll();
        long long l = parse_ll();
        // skip to ']'
        while (i < n && s[i] != ']') i++;
        if (i < n && s[i] == ']') i++;
        items.push_back({key, q, v, m, l});
        // skip to next '"' or '}' 
        while (i < n && s[i] != '"' && s[i] != '}') i++;
        if (i < n && s[i] == '}') { i++; break; }
    }
    return items;
}

struct Solution {
    vector<long long> cnt;
    long long value;
    long long mass;
    long long vol;
};

static inline long long clampLL(long long x, long long lo, long long hi) {
    if (x < lo) return lo;
    if (x > hi) return hi;
    return x;
}

Solution evalSolution(const vector<Type>& types, const vector<long long>& cnt) {
    long long mass=0, vol=0, val=0;
    int n = (int)types.size();
    for (int i=0;i<n;i++) {
        long long c = cnt[i];
        if (c < 0) c = 0;
        if (c > types[i].q) c = types[i].q;
        mass += types[i].m * c;
        vol  += types[i].l * c;
        val  += types[i].v * c;
    }
    // Enforce feasibility
    if (mass > MASS_CAP || vol > VOL_CAP) {
        // infeasible, return zero
        return Solution{vector<long long>(n,0),0,0,0};
    }
    return Solution{cnt, val, mass, vol};
}

Solution greedyFill(const vector<Type>& types, const vector<long long>& base, double lambda) {
    int n = (int)types.size();
    vector<long long> cnt = base;
    long long mass=0, vol=0, val=0;
    for (int i=0;i<n;i++) {
        long long c = clampLL(cnt[i], 0, types[i].q);
        cnt[i] = c;
        mass += types[i].m * c;
        vol  += types[i].l * c;
        val  += types[i].v * c;
    }
    long long remM = MASS_CAP - mass;
    long long remL = VOL_CAP - vol;
    if (remM < 0 || remL < 0) {
        // base infeasible; return base as is (will be evaluated as infeasible outside)
        return evalSolution(types, cnt);
    }

    while (true) {
        int best = -1;
        double bestScore = -1.0;
        for (int i=0;i<n;i++) {
            if (cnt[i] >= types[i].q) continue;
            if (types[i].m > remM || types[i].l > remL) continue;
            double normM = (double)types[i].m / (double)MASS_CAP;
            double normL = (double)types[i].l / (double)VOL_CAP;
            double denom = lambda * normM + (1.0 - lambda) * normL;
            if (denom <= 0) continue;
            double score = (double)types[i].v / denom;
            if (score > bestScore) { bestScore = score; best = i; }
        }
        if (best == -1) break;
        long long canM = remM / types[best].m;
        long long canL = remL / types[best].l;
        long long canQ = types[best].q - cnt[best];
        long long add = min(canQ, min(canM, canL));
        if (add <= 0) break;
        cnt[best] += add;
        remM -= add * types[best].m;
        remL -= add * types[best].l;
        val  += add * types[best].v;
    }
    return evalSolution(types, cnt);
}

Solution greedyMaxRatio(const vector<Type>& types) {
    int n = (int)types.size();
    vector<int> ord(n);
    iota(ord.begin(), ord.end(), 0);
    vector<double> ratio(n, 0.0);
    for (int i=0;i<n;i++) {
        double a = (double)types[i].m / (double)MASS_CAP;
        double b = (double)types[i].l / (double)VOL_CAP;
        double d = max(a, b);
        if (d <= 0) ratio[i] = 0;
        else ratio[i] = (double)types[i].v / d;
    }
    sort(ord.begin(), ord.end(), [&](int a, int b){
        if (ratio[a] != ratio[b]) return ratio[a] > ratio[b];
        return types[a].v > types[b].v;
    });

    vector<long long> cnt(n, 0);
    long long remM = MASS_CAP, remL = VOL_CAP;
    for (int id : ord) {
        if (types[id].m > remM || types[id].l > remL) continue;
        long long k = min((long long)types[id].q, min(remM / types[id].m, remL / types[id].l));
        if (k > 0) {
            cnt[id] = k;
            remM -= k * types[id].m;
            remL -= k * types[id].l;
        }
    }
    return evalSolution(types, cnt);
}

Solution solveDPScaled(const vector<Type>& types, long long scaleM, long long scaleL) {
    int n = (int)types.size();
    long long Msc = MASS_CAP / scaleM; // floor
    long long Lsc = VOL_CAP  / scaleL; // floor
    int MS = (int)Msc;
    int LS = (int)Lsc;
    if (MS <= 0 || LS <= 0) {
        vector<long long> zero(n,0);
        return evalSolution(types, zero);
    }

    // Build pseudo items via binary splitting
    vector<PItem> items;
    items.reserve(200);
    for (int i=0;i<n;i++) {
        long long qcap = min(types[i].q, min(MASS_CAP / max(1LL, types[i].m), VOL_CAP / max(1LL, types[i].l)));
        long long j = 1;
        long long Q = qcap;
        while (Q > 0) {
            long long chunk = min(j, Q);
            long long tm = types[i].m * chunk;
            long long tl = types[i].l * chunk;
            int wM = (int)((tm + scaleM - 1) / scaleM);
            int wL = (int)((tl + scaleL - 1) / scaleL);
            if (wM <= MS && wL <= LS) {
                items.push_back({i, (int)chunk, types[i].v * chunk, wM, wL});
            }
            Q -= chunk;
            j <<= 1;
        }
    }

    int W = (LS + 1);
    int SZ = (MS + 1) * W;

    // DP arrays
    vector<long long> dp(SZ, 0);
    vector<int> prevItem(SZ, -1);
    vector<int> prevIdx(SZ, -1);

    for (int idxItem = 0; idxItem < (int)items.size(); idxItem++) {
        const PItem &p = items[idxItem];
        for (int m = MS; m >= p.wM; --m) {
            int base_m = m * W;
            int prev_m = (m - p.wM) * W;
            for (int v = LS; v >= p.wL; --v) {
                int idx = base_m + v;
                int pidx = prev_m + (v - p.wL);
                long long cand = dp[pidx] + p.val;
                if (cand > dp[idx]) {
                    dp[idx] = cand;
                    prevItem[idx] = idxItem;
                    prevIdx[idx] = pidx;
                }
            }
        }
    }

    // Find best state
    long long bestVal = -1;
    int bestState = 0;
    for (int i=0;i<SZ;i++) {
        if (dp[i] > bestVal) { bestVal = dp[i]; bestState = i; }
    }

    vector<long long> cnt(n, 0);
    int cur = bestState;
    while (cur >= 0 && prevItem[cur] != -1) {
        int it = prevItem[cur];
        cnt[items[it].type] += items[it].mult;
        cur = prevIdx[cur];
    }

    // Ensure counts do not exceed caps
    for (int i=0;i<n;i++) {
        cnt[i] = clampLL(cnt[i], 0, types[i].q);
    }

    Solution sol = evalSolution(types, cnt);

    // Use leftover capacity to greedily fill
    vector<double> lambdas = {0.0, 0.33, 0.5, 0.67, 1.0};
    Solution best = sol;
    for (double lam : lambdas) {
        Solution s2 = greedyFill(types, sol.cnt, lam);
        if (s2.value > best.value) best = s2;
    }
    return best;
}

Solution greedyMulti(const vector<Type>& types) {
    vector<double> lambdas = {0.0, 0.25, 0.5, 0.75, 1.0};
    Solution best{{},0,0,0};
    int n = (int)types.size();
    for (double lam : lambdas) {
        vector<int> ord(n);
        iota(ord.begin(), ord.end(), 0);
        vector<double> ratio(n, 0.0);
        for (int i=0;i<n;i++) {
            double normM = (double)types[i].m / (double)MASS_CAP;
            double normL = (double)types[i].l / (double)VOL_CAP;
            double denom = lam * normM + (1.0 - lam) * normL;
            if (denom <= 0) ratio[i] = 0;
            else ratio[i] = (double)types[i].v / denom;
        }
        sort(ord.begin(), ord.end(), [&](int a, int b){
            if (ratio[a] != ratio[b]) return ratio[a] > ratio[b];
            return types[a].v > types[b].v;
        });

        vector<long long> cnt(n, 0);
        long long remM = MASS_CAP, remL = VOL_CAP;
        for (int id : ord) {
            if (types[id].m > remM || types[id].l > remL) continue;
            long long add = min((long long)types[id].q, min(remM / types[id].m, remL / types[id].l));
            if (add > 0) {
                cnt[id] = add;
                remM -= add * types[id].m;
                remL -= add * types[id].l;
            }
        }
        Solution s = evalSolution(types, cnt);
        if (s.value > best.value) best = s;
    }
    Solution smax = greedyMaxRatio(types);
    if (smax.value > best.value) best = smax;
    return best;
}

Solution pairwiseImprove(const vector<Type>& types, Solution sol) {
    int n = (int)types.size();
    vector<long long> cnt = sol.cnt;
    long long mass = sol.mass, vol = sol.vol, val = sol.value;
    bool improved = true;
    int iter = 0;
    while (improved && iter < 200) {
        improved = false;
        iter++;
        for (int i=0;i<n && !improved;i++) {
            if (cnt[i] >= types[i].q) continue;
            for (int j=0;j<n && !improved;j++) {
                if (cnt[j] <= 0) continue;
                if (i == j) continue;
                long long nmass = mass + types[i].m - types[j].m;
                long long nvol  = vol  + types[i].l - types[j].l;
                if (nmass <= MASS_CAP && nvol <= VOL_CAP && types[i].v > types[j].v) {
                    mass = nmass; vol = nvol; val += (types[i].v - types[j].v);
                    cnt[i]++; cnt[j]--;
                    improved = true;
                }
            }
        }
    }
    return evalSolution(types, cnt);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<Type> types = parseInput(cin);
    int n = (int)types.size();
    // Cap q by feasibility
    for (int i=0;i<n;i++) {
        long long capM = (types[i].m > 0) ? MASS_CAP / types[i].m : 0;
        long long capL = (types[i].l > 0) ? VOL_CAP / types[i].l : 0;
        long long qcap = min(types[i].q, min(capM, capL));
        types[i].q = max(0LL, qcap);
    }

    // Generate candidates
    vector<pair<long long,long long>> scales = {
        {100000, 125000}, // 200 x 200
        {100000, 100000}, // 200 x 250
        {50000,  125000}, // 400 x 200
        {200000, 125000}, // 100 x 200
    };

    Solution best{{},0,0,0};

    // Greedy baselines
    Solution g = greedyMulti(types);
    if (g.value > best.value) best = g;

    // DP candidates
    for (auto sc : scales) {
        Solution s = solveDPScaled(types, sc.first, sc.second);
        if (s.value > best.value) best = s;
    }

    // Final light local improvement
    Solution improved = pairwiseImprove(types, best);
    if (improved.value > best.value) best = improved;

    // Output JSON with same keys in same order
    cout << "{\n";
    for (int i=0;i<n;i++) {
        cout << " \"" << types[i].name << "\": " << clampLL(best.cnt[i], 0, types[i].q);
        if (i + 1 < n) cout << ",\n";
        else cout << "\n";
    }
    cout << "}\n";
    return 0;
}