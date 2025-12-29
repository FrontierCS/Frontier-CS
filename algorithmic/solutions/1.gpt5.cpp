#include <bits/stdc++.h>
using namespace std;

static const long long M_CAP = 20000000LL; // mg
static const long long L_CAP = 25000000LL; // uL

struct Item {
    string name;
    long long q, v, m, l;
    int idx;
};

struct Parser {
    string s;
    size_t i=0;
    Parser(const string& str): s(str), i(0) {}
    void skip() {
        while (i < s.size() && (s[i]==' ' || s[i]=='\n' || s[i]=='\r' || s[i]=='\t')) i++;
    }
    bool peek(char c) {
        skip();
        return i < s.size() && s[i]==c;
    }
    void expect(char c) {
        skip();
        if (i>=s.size() || s[i]!=c) {
            // try to recover
        } else {
            i++;
        }
    }
    string parseString() {
        skip();
        string out;
        if (i < s.size() && s[i]=='"') {
            i++;
            while (i < s.size()) {
                char c = s[i++];
                if (c=='\\') {
                    if (i < s.size()) {
                        char nxt = s[i++];
                        // For simplicity, just append the escaped char
                        out.push_back(nxt);
                    }
                } else if (c=='"') {
                    break;
                } else {
                    out.push_back(c);
                }
            }
        }
        return out;
    }
    long long parseNumber() {
        skip();
        bool neg=false;
        if (i<s.size() && s[i]=='-') { neg=true; i++; }
        long long x=0;
        while (i < s.size() && s[i]>='0' && s[i]<='9') {
            x = x*10 + (s[i]-'0');
            i++;
        }
        return neg? -x : x;
    }
};

struct Solution {
    vector<long long> cnt;
    long long val=0;
    long long m_used=0;
    long long l_used=0;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    // Read entire input
    std::string input, line;
    {
        std::ostringstream oss;
        oss << cin.rdbuf();
        input = oss.str();
    }

    // Parse JSON
    Parser p(input);
    vector<Item> items;
    p.expect('{');
    int idx = 0;
    while (true) {
        p.skip();
        if (p.peek('}')) { p.expect('}'); break; }
        string key = p.parseString();
        p.expect(':');
        p.expect('[');
        vector<long long> arr;
        while (true) {
            long long num = p.parseNumber();
            arr.push_back(num);
            p.skip();
            if (p.peek(',')) { p.expect(','); p.skip(); if (p.peek(']')) { p.expect(']'); break; } }
            else if (p.peek(']')) { p.expect(']'); break; }
            else {
                // keep parsing
            }
        }
        Item it;
        it.name = key;
        if (arr.size() >= 4) {
            it.q = arr[0];
            it.v = arr[1];
            it.m = arr[2];
            it.l = arr[3];
        } else {
            it.q = 0; it.v=0; it.m=1; it.l=1;
        }
        it.idx = idx++;
        items.push_back(it);
        p.skip();
        if (p.peek(',')) { p.expect(','); continue; }
        else if (p.peek('}')) { p.expect('}'); break; }
        else {
            // continue
        }
    }

    int n = (int)items.size();
    if (n == 0) {
        cout << "{}\n";
        return 0;
    }

    // Precompute upper bound per item (can't exceed q, M/m, L/l)
    vector<long long> r(n, 0);
    for (int i=0;i<n;i++) {
        if (items[i].m > 0 && items[i].l > 0 && items[i].v > 0) {
            long long byM = items[i].m > 0 ? (M_CAP / items[i].m) : (long long)1e18;
            long long byL = items[i].l > 0 ? (L_CAP / items[i].l) : (long long)1e18;
            long long rr = min(items[i].q, min(byM, byL));
            r[i] = max(0LL, rr);
        } else {
            r[i] = 0;
        }
    }

    // Precompute normalized mass and volume
    vector<double> nm(n), nl(n);
    for (int i=0;i<n;i++) {
        nm[i] = (double)items[i].m / (double)M_CAP;
        nl[i] = (double)items[i].l / (double)L_CAP;
    }

    auto now = [](){ return chrono::high_resolution_clock::now(); };
    auto start = now();
    auto elapsed_ms = [&](double limit_ms){
        auto t = now();
        double ms = chrono::duration<double, std::milli>(t - start).count();
        return ms;
    };

    // Greedy build function
    struct WeightSpec { int type; double a,b; };
    auto greedy_build = [&](const WeightSpec& ws)->Solution {
        vector<int> order(n);
        iota(order.begin(), order.end(), 0);
        vector<double> dens(n, 0.0);
        for (int i=0;i<n;i++) {
            if (r[i] <= 0) { dens[i] = -1e300; continue; }
            if (ws.type == 0) {
                double denom = ws.a * (double)items[i].m + ws.b * (double)items[i].l;
                if (denom <= 0) denom = 1e-18;
                dens[i] = (double)items[i].v / denom;
            } else if (ws.type == 1) {
                double denom = max(nm[i], nl[i]);
                if (denom <= 0) denom = 1e-18;
                dens[i] = (double)items[i].v / denom;
            } else if (ws.type == 2) {
                double denom = hypot(nm[i], nl[i]);
                if (denom <= 0) denom = 1e-18;
                dens[i] = (double)items[i].v / denom;
            } else if (ws.type == 3) {
                dens[i] = (double)items[i].v;
            } else {
                double denom = ws.a * (double)items[i].m + ws.b * (double)items[i].l;
                if (denom <= 0) denom = 1e-18;
                dens[i] = (double)items[i].v / denom;
            }
        }
        stable_sort(order.begin(), order.end(), [&](int i, int j){
            if (dens[i] != dens[j]) return dens[i] > dens[j];
            if (items[i].v != items[j].v) return items[i].v > items[j].v;
            double wi = (ws.a * (double)items[i].m + ws.b * (double)items[i].l);
            double wj = (ws.a * (double)items[j].m + ws.b * (double)items[j].l);
            return wi < wj;
        });

        Solution sol;
        sol.cnt.assign(n, 0);
        long long Mm = M_CAP, Ll = L_CAP;
        long long val = 0;
        for (int idxi : order) {
            if (r[idxi] <= 0) continue;
            long long can_by_M = items[idxi].m > 0 ? (Mm / items[idxi].m) : 0;
            long long can_by_L = items[idxi].l > 0 ? (Ll / items[idxi].l) : 0;
            long long can = min(r[idxi], min(can_by_M, can_by_L));
            if (can <= 0) continue;
            sol.cnt[idxi] += can;
            val += can * items[idxi].v;
            Mm -= can * items[idxi].m;
            Ll -= can * items[idxi].l;
            if (Mm <= 0 || Ll <= 0) break;
        }
        sol.val = val;
        sol.m_used = M_CAP - Mm;
        sol.l_used = L_CAP - Ll;
        return sol;
    };

    // Improvement heuristic
    auto improve = [&](Solution& sol, const WeightSpec& ws, double time_ms_budget){
        // Precompute removal order by lowest density under ws
        vector<double> remDensity(n, 0.0);
        for (int i=0;i<n;i++) {
            if (ws.type == 0) {
                double denom = ws.a * (double)items[i].m + ws.b * (double)items[i].l;
                if (denom <= 0) denom = 1e-18;
                remDensity[i] = (double)items[i].v / denom;
            } else if (ws.type == 1) {
                double denom = max(nm[i], nl[i]);
                if (denom <= 0) denom = 1e-18;
                remDensity[i] = (double)items[i].v / denom;
            } else if (ws.type == 2) {
                double denom = hypot(nm[i], nl[i]);
                if (denom <= 0) denom = 1e-18;
                remDensity[i] = (double)items[i].v / denom;
            } else if (ws.type == 3) {
                // For removals under type 3 (value only), define density as value per normalized combined weight
                double denom = (double)items[i].m / (double)M_CAP + (double)items[i].l / (double)L_CAP;
                if (denom <= 0) denom = 1e-18;
                remDensity[i] = (double)items[i].v / denom;
            } else {
                double denom = ws.a * (double)items[i].m + ws.b * (double)items[i].l;
                if (denom <= 0) denom = 1e-18;
                remDensity[i] = (double)items[i].v / denom;
            }
        }
        vector<int> remOrder(n);
        iota(remOrder.begin(), remOrder.end(), 0);
        stable_sort(remOrder.begin(), remOrder.end(), [&](int i, int j){
            if (remDensity[i] != remDensity[j]) return remDensity[i] < remDensity[j];
            return items[i].v < items[j].v;
        });

        vector<int> addOrder(n);
        iota(addOrder.begin(), addOrder.end(), 0);
        stable_sort(addOrder.begin(), addOrder.end(), [&](int i, int j){
            if (items[i].v != items[j].v) return items[i].v > items[j].v;
            double di = nm[i] + nl[i];
            double dj = nm[j] + nl[j];
            return di < dj;
        });

        long long Mm = M_CAP - sol.m_used;
        long long Ll = L_CAP - sol.l_used;
        long long curVal = sol.val;

        auto time_ok = [&](){
            return elapsed_ms(0) < time_ms_budget;
        };

        bool improved_any = true;
        int outer_iters = 0;
        while (improved_any && time_ok()) {
            improved_any = false;
            outer_iters++;
            if (outer_iters > 100) break;
            for (int j_idx = 0; j_idx < n && time_ok(); j_idx++) {
                int j = addOrder[j_idx];
                if (r[j] <= 0) continue;
                if (sol.cnt[j] >= r[j]) continue;
                // Try to add as many as fits directly
                if (Mm >= items[j].m && Ll >= items[j].l) {
                    long long can_by_M = items[j].m > 0 ? (Mm / items[j].m) : 0;
                    long long can_by_L = items[j].l > 0 ? (Ll / items[j].l) : 0;
                    long long quota = r[j] - sol.cnt[j];
                    long long take = min(quota, min(can_by_M, can_by_L));
                    if (take > 0) {
                        sol.cnt[j] += take;
                        Mm -= take * items[j].m;
                        Ll -= take * items[j].l;
                        curVal += take * items[j].v;
                        improved_any = true;
                    }
                }
                // Attempt single-item addition by removing low-density items
                bool changed = true;
                int inner_added = 0;
                while (changed && time_ok()) {
                    changed = false;
                    if (sol.cnt[j] >= r[j]) break;
                    if (Mm >= items[j].m && Ll >= items[j].l) {
                        sol.cnt[j] += 1;
                        Mm -= items[j].m;
                        Ll -= items[j].l;
                        curVal += items[j].v;
                        improved_any = true;
                        changed = true;
                        inner_added++;
                        if (inner_added > 64) break; // prevent long loops on single item
                        continue;
                    }
                    long long needM = (items[j].m > Mm) ? (items[j].m - Mm) : 0LL;
                    long long needL = (items[j].l > Ll) ? (items[j].l - Ll) : 0LL;
                    if (needM == 0 && needL == 0) continue;

                    long long freedM = 0, freedL = 0;
                    long long removedVal = 0;
                    vector<long long> removedCnt(n, 0);
                    for (int i_idx = 0; i_idx < n; i_idx++) {
                        int i2 = remOrder[i_idx];
                        if (i2 == j) continue;
                        long long have = sol.cnt[i2];
                        if (have <= 0) continue;
                        long long reqM = 0, reqL = 0;
                        if (needM > freedM) reqM = (needM - freedM + items[i2].m - 1) / items[i2].m;
                        if (needL > freedL) reqL = (needL - freedL + items[i2].l - 1) / items[i2].l;
                        long long need = max(reqM, reqL);
                        if (need <= 0) continue;
                        long long maxByValue = LLONG_MAX;
                        if (items[i2].v > 0) {
                            if (removedVal < items[j].v) {
                                long long cap = (items[j].v - 1 - removedVal) / items[i2].v;
                                if (cap < 0) cap = 0;
                                maxByValue = cap;
                            } else {
                                maxByValue = 0;
                            }
                        }
                        long long take = min(have, need);
                        take = min(take, maxByValue);
                        if (take <= 0) continue;
                        removedCnt[i2] += take;
                        freedM += take * items[i2].m;
                        freedL += take * items[i2].l;
                        removedVal += take * items[i2].v;
                        if ((Mm + freedM) >= items[j].m && (Ll + freedL) >= items[j].l) break;
                    }
                    if ((Mm + freedM) >= items[j].m && (Ll + freedL) >= items[j].l && removedVal < items[j].v) {
                        // Commit removals
                        for (int k=0;k<n;k++) {
                            if (removedCnt[k] > 0) {
                                sol.cnt[k] -= removedCnt[k];
                            }
                        }
                        Mm += freedM;
                        Ll += freedL;
                        curVal -= removedVal;
                        // Add one j
                        sol.cnt[j] += 1;
                        Mm -= items[j].m;
                        Ll -= items[j].l;
                        curVal += items[j].v;
                        improved_any = true;
                        changed = true;
                        inner_added++;
                        if (inner_added > 64) break;
                    } else {
                        // Can't improve by adding j via removal
                        break;
                    }
                }
            }
        }

        sol.val = curVal;
        sol.m_used = M_CAP - Mm;
        sol.l_used = L_CAP - Ll;

        // Final greedy fill of any leftover capacity with low-value items just to fill
        // Try to add anything that fits by density (high to low)
        vector<int> fillOrder(n);
        iota(fillOrder.begin(), fillOrder.end(), 0);
        vector<double> densFill(n, 0.0);
        for (int i=0;i<n;i++) {
            double denom = (double)items[i].m / (double)M_CAP + (double)items[i].l / (double)L_CAP;
            if (denom <= 0) denom = 1e-18;
            densFill[i] = (double)items[i].v / denom;
        }
        stable_sort(fillOrder.begin(), fillOrder.end(), [&](int a, int b){
            if (densFill[a] != densFill[b]) return densFill[a] > densFill[b];
            return items[a].v > items[b].v;
        });
        long long Mm2 = M_CAP - sol.m_used;
        long long Ll2 = L_CAP - sol.l_used;
        for (int iidx : fillOrder) {
            if (!time_ok()) break;
            long long quota = r[iidx] - sol.cnt[iidx];
            if (quota <= 0) continue;
            long long can_by_M = items[iidx].m > 0 ? (Mm2 / items[iidx].m) : 0;
            long long can_by_L = items[iidx].l > 0 ? (Ll2 / items[iidx].l) : 0;
            long long take = min(quota, min(can_by_M, can_by_L));
            if (take > 0) {
                sol.cnt[iidx] += take;
                sol.val += take * items[iidx].v;
                Mm2 -= take * items[iidx].m;
                Ll2 -= take * items[iidx].l;
            }
        }
        sol.m_used = M_CAP - Mm2;
        sol.l_used = L_CAP - Ll2;
    };

    // Prepare weight specs
    vector<WeightSpec> weights;
    // Linear combinations over t in [0,1]
    const int T1 = 10;
    for (int k=0;k<=T1;k++) {
        double t = (double)k / (double)T1;
        WeightSpec ws{0, t / (double)M_CAP, (1.0 - t) / (double)L_CAP};
        weights.push_back(ws);
    }
    for (int k=0;k<=9;k++) {
        double t = 0.05 + 0.1 * k;
        WeightSpec ws{0, t / (double)M_CAP, (1.0 - t) / (double)L_CAP};
        weights.push_back(ws);
    }
    // Some biased weights
    vector<double> gammas = {0.25, 0.5, 1.0, 2.0, 4.0};
    for (double g : gammas) {
        WeightSpec ws{0, 1.0/(double)M_CAP, g/(double)L_CAP};
        weights.push_back(ws);
    }
    // Special measures
    weights.push_back(WeightSpec{1, 0.0, 0.0}); // max(nm, nl)
    weights.push_back(WeightSpec{2, 0.0, 0.0}); // L2 norm
    weights.push_back(WeightSpec{3, 0.0, 0.0}); // pure value

    // Initialize best solution as empty
    Solution best;
    best.cnt.assign(n, 0);
    best.val = 0;
    best.m_used = 0;
    best.l_used = 0;

    double time_budget_ms = 950.0; // Slightly less than 1s

    // Try all weight specs with improvements within time budget
    for (size_t wi = 0; wi < weights.size(); wi++) {
        if (elapsed_ms(0) > time_budget_ms) break;
        Solution sol = greedy_build(weights[wi]);
        if (elapsed_ms(0) > time_budget_ms) {
            if (sol.val > best.val) best = sol;
            break;
        }
        // Improvement with limited time slice
        double remaining = time_budget_ms - elapsed_ms(0);
        double alloc = max(10.0, remaining / (double)(weights.size() - wi + 1));
        improve(sol, weights[wi], elapsed_ms(0) + alloc);
        if (sol.val > best.val) best = sol;
    }

    // Safety: ensure feasibility
    long long total_m = 0, total_l = 0;
    for (int i=0;i<n;i++) {
        best.cnt[i] = min(best.cnt[i], r[i]);
        if (best.cnt[i] < 0) best.cnt[i] = 0;
        total_m += best.cnt[i] * items[i].m;
        total_l += best.cnt[i] * items[i].l;
    }
    if (total_m > M_CAP || total_l > L_CAP) {
        // Trim greedily lowest density until feasible
        vector<int> order(n);
        iota(order.begin(), order.end(), 0);
        vector<double> dens(n);
        for (int i=0;i<n;i++) {
            double denom = (double)items[i].m / (double)M_CAP + (double)items[i].l / (double)L_CAP;
            if (denom <= 0) denom = 1e-18;
            dens[i] = (double)items[i].v / denom;
        }
        stable_sort(order.begin(), order.end(), [&](int a, int b){
            if (dens[a] != dens[b]) return dens[a] < dens[b];
            return items[a].v < items[b].v;
        });
        for (int idxi : order) {
            while ((total_m > M_CAP || total_l > L_CAP) && best.cnt[idxi] > 0) {
                best.cnt[idxi]--;
                total_m -= items[idxi].m;
                total_l -= items[idxi].l;
            }
            if (total_m <= M_CAP && total_l <= L_CAP) break;
        }
    }

    // Output JSON with same keys/order as input
    cout << "{\n";
    for (int i=0;i<n;i++) {
        cout << " \"" << items[i].name << "\": " << best.cnt[i];
        if (i+1<n) cout << ",\n";
        else cout << "\n";
    }
    cout << "}\n";
    return 0;
}