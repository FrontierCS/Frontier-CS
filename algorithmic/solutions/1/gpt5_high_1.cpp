#include <bits/stdc++.h>
using namespace std;

struct Item {
    string name;
    long long q, v, m, l;
    int idx;
};

struct Parser {
    string s;
    size_t pos = 0;

    Parser(const string& str) : s(str), pos(0) {}

    void skipWS() {
        while (pos < s.size() && isspace((unsigned char)s[pos])) pos++;
    }

    bool match(char c) {
        skipWS();
        if (pos < s.size() && s[pos] == c) {
            pos++;
            return true;
        }
        return false;
    }

    void expect(char c) {
        skipWS();
        if (pos >= s.size() || s[pos] != c) {
            // Fallback: try to progress to avoid infinite loop
            // but in contest, just ensure format is correct.
            // For safety, move pos to end.
            pos = s.size();
            return;
        }
        pos++;
    }

    string parseString() {
        skipWS();
        string res;
        if (pos < s.size() && s[pos] == '"') {
            pos++;
            while (pos < s.size()) {
                char c = s[pos++];
                if (c == '\\') {
                    if (pos < s.size()) {
                        char next = s[pos++];
                        // Handle simple escapes
                        if (next == '"' || next == '\\' || next == '/') res.push_back(next);
                        else if (next == 'b') res.push_back('\b');
                        else if (next == 'f') res.push_back('\f');
                        else if (next == 'n') res.push_back('\n');
                        else if (next == 'r') res.push_back('\r');
                        else if (next == 't') res.push_back('\t');
                        else res.push_back(next);
                    }
                } else if (c == '"') {
                    break;
                } else {
                    res.push_back(c);
                }
            }
        }
        return res;
    }

    long long parseInt() {
        skipWS();
        bool neg = false;
        if (pos < s.size() && (s[pos] == '-' || s[pos] == '+')) {
            neg = (s[pos] == '-');
            pos++;
        }
        long long val = 0;
        while (pos < s.size() && isdigit((unsigned char)s[pos])) {
            val = val * 10 + (s[pos] - '0');
            pos++;
        }
        return neg ? -val : val;
    }

    vector<Item> parse() {
        vector<Item> items;
        expect('{');
        while (true) {
            skipWS();
            if (pos >= s.size()) break;
            if (s[pos] == '}') { pos++; break; }
            string key = parseString();
            expect(':');
            // parse array [q, v, m, l]
            expect('[');
            long long q = parseInt(); expect(',');
            long long v = parseInt(); expect(',');
            long long m = parseInt(); expect(',');
            long long l = parseInt();
            expect(']');
            Item it;
            it.name = key; it.q = q; it.v = v; it.m = m; it.l = l;
            it.idx = (int)items.size();
            items.push_back(it);
            skipWS();
            if (pos < s.size() && s[pos] == ',') pos++;
        }
        return items;
    }
};

struct Solution {
    vector<long long> cnt;
    long long val=0, usedM=0, usedL=0;
};

static const long long CAP_M = 20000000LL; // mg
static const long long CAP_L = 25000000LL; // uL

struct HeuristicSolver {
    vector<Item> items;
    int n;
    vector<long long> qLim;

    HeuristicSolver(const vector<Item>& its) : items(its) {
        n = (int)items.size();
        qLim.resize(n);
        for (int i = 0; i < n; ++i) {
            long long qm = items[i].m > 0 ? (CAP_M / items[i].m) : 0;
            long long ql = items[i].l > 0 ? (CAP_L / items[i].l) : 0;
            qLim[i] = min(items[i].q, min(qm, ql));
        }
    }

    Solution evaluate(const vector<long long>& cnt) {
        Solution s;
        s.cnt = cnt;
        long long M=0, L=0, V=0;
        for (int i = 0; i < n; ++i) {
            long long c = cnt[i];
            if (c < 0) { s.val = -1; return s; }
            if (c > qLim[i]) { s.val = -1; return s; }
            V += c * items[i].v;
            M += c * items[i].m;
            L += c * items[i].l;
        }
        if (M > CAP_M || L > CAP_L) { s.val = -1; return s; }
        s.val = V; s.usedM = M; s.usedL = L;
        return s;
    }

    vector<int> sorted_by_ratio(double alpha) {
        vector<pair<double,int>> arr;
        arr.reserve(n);
        for (int i = 0; i < n; ++i) {
            double cm = (double)items[i].m / (double)CAP_M;
            double cl = (double)items[i].l / (double)CAP_L;
            double denom = alpha * cm + (1.0 - alpha) * cl;
            double ratio = (denom > 0) ? ( (double)items[i].v / denom ) : 1e300;
            arr.emplace_back(ratio, i);
        }
        sort(arr.begin(), arr.end(), [&](auto& a, auto& b){
            if (a.first != b.first) return a.first > b.first;
            // tie-breakers: higher value, lower mass+volume
            const Item &ia = items[a.second], &ib = items[b.second];
            if (ia.v != ib.v) return ia.v > ib.v;
            long long sa = ia.m + ia.l, sb = ib.m + ib.l;
            return sa < sb;
        });
        vector<int> order; order.reserve(n);
        for (auto &p : arr) order.push_back(p.second);
        return order;
    }

    vector<int> sorted_by_maxnorm() {
        vector<pair<double,int>> arr;
        arr.reserve(n);
        for (int i = 0; i < n; ++i) {
            double cnm = (double)items[i].m / (double)CAP_M;
            double cnl = (double)items[i].l / (double)CAP_L;
            double denom = max(cnm, cnl);
            double ratio = (denom > 0) ? ((double)items[i].v / denom) : 1e300;
            arr.emplace_back(ratio, i);
        }
        sort(arr.begin(), arr.end(), [&](auto& a, auto& b){
            if (a.first != b.first) return a.first > b.first;
            const Item &ia = items[a.second], &ib = items[b.second];
            if (ia.v != ib.v) return ia.v > ib.v;
            long long sa = ia.m + ia.l, sb = ib.m + ib.l;
            return sa < sb;
        });
        vector<int> order; order.reserve(n);
        for (auto &p : arr) order.push_back(p.second);
        return order;
    }

    vector<long long> fill_sorted_order(const vector<int>& order) {
        vector<long long> cnt(n, 0);
        long long RM = CAP_M, RL = CAP_L;
        for (int idx : order) {
            if (qLim[idx] <= 0) continue;
            long long cm = items[idx].m, cl = items[idx].l;
            if (cm == 0 || cl == 0) continue; // should not happen
            long long canM = RM / cm;
            long long canL = RL / cl;
            long long add = min(qLim[idx] - cnt[idx], min(canM, canL));
            if (add <= 0) continue;
            cnt[idx] += add;
            RM -= add * cm;
            RL -= add * cl;
        }
        return cnt;
    }

    vector<long long> fill_incremental_static_ratio(double alpha, vector<long long> startCnt = {}) {
        vector<long long> cnt = startCnt.empty() ? vector<long long>(n, 0) : startCnt;
        long long usedM = 0, usedL = 0;
        if (!startCnt.empty()) {
            for (int i = 0; i < n; ++i) {
                usedM += cnt[i] * items[i].m;
                usedL += cnt[i] * items[i].l;
            }
        }
        long long RM = CAP_M - usedM, RL = CAP_L - usedL;
        if (RM < 0 || RL < 0) return cnt;

        // Precompute static scores
        vector<double> score(n, -1e300);
        for (int i = 0; i < n; ++i) {
            double cm = (double)items[i].m / (double)CAP_M;
            double cl = (double)items[i].l / (double)CAP_L;
            double denom = alpha * cm + (1.0 - alpha) * cl;
            score[i] = (denom > 0) ? ((double)items[i].v / denom) : 1e300;
        }

        while (true) {
            int best = -1;
            double bestScore = -1e300;
            for (int i = 0; i < n; ++i) {
                if (cnt[i] >= qLim[i]) continue;
                if (items[i].m <= RM && items[i].l <= RL) {
                    double sc = score[i];
                    if (sc > bestScore) {
                        bestScore = sc; best = i;
                    }
                }
            }
            if (best == -1) break;
            cnt[best] += 1;
            RM -= items[best].m;
            RL -= items[best].l;
        }
        return cnt;
    }

    vector<long long> fill_incremental_dynamic_ratio(vector<long long> startCnt = {}) {
        vector<long long> cnt = startCnt.empty() ? vector<long long>(n, 0) : startCnt;
        long long usedM = 0, usedL = 0;
        if (!startCnt.empty()) {
            for (int i = 0; i < n; ++i) {
                usedM += cnt[i] * items[i].m;
                usedL += cnt[i] * items[i].l;
            }
        }
        long long RM = CAP_M - usedM, RL = CAP_L - usedL;
        if (RM < 0 || RL < 0) return cnt;

        while (true) {
            int best = -1;
            double bestScore = -1e300;
            double wm = (RM > 0) ? (1.0 / (double)RM) : 1e300;
            double wl = (RL > 0) ? (1.0 / (double)RL) : 1e300;
            for (int i = 0; i < n; ++i) {
                if (cnt[i] >= qLim[i]) continue;
                if (items[i].m <= RM && items[i].l <= RL) {
                    double denom = items[i].m * wm + items[i].l * wl;
                    double sc = denom > 0 ? ((double)items[i].v / denom) : 1e300;
                    if (sc > bestScore) {
                        bestScore = sc; best = i;
                    }
                }
            }
            if (best == -1) break;
            cnt[best] += 1;
            RM -= items[best].m;
            RL -= items[best].l;
        }
        return cnt;
    }

    Solution best_of_candidates(const vector<vector<long long>>& cands) {
        Solution best;
        best.val = -1;
        for (auto &cnt : cands) {
            Solution s = evaluate(cnt);
            if (s.val > best.val) best = s;
        }
        if (best.val < 0) {
            // fallback to empty
            best = evaluate(vector<long long>(n,0));
        }
        return best;
    }

    vector<long long> greedy_refill(vector<long long> cnt, long long RM, long long RL, double alpha) {
        // refill incrementally with static ratio alpha
        // ensure counts satisfy qLim and capacity
        // We'll select best each step
        vector<double> score(n, -1e300);
        for (int i = 0; i < n; ++i) {
            double cm = (double)items[i].m / (double)CAP_M;
            double cl = (double)items[i].l / (double)CAP_L;
            double denom = alpha * cm + (1.0 - alpha) * cl;
            score[i] = (denom > 0) ? ((double)items[i].v / denom) : 1e300;
        }
        while (true) {
            int best = -1;
            double bestScore = -1e300;
            for (int i = 0; i < n; ++i) {
                if (cnt[i] >= qLim[i]) continue;
                if (items[i].m <= RM && items[i].l <= RL) {
                    double sc = score[i];
                    if (sc > bestScore) {
                        bestScore = sc; best = i;
                    }
                }
            }
            if (best == -1) break;
            cnt[best] += 1;
            RM -= items[best].m;
            RL -= items[best].l;
        }
        return cnt;
    }

    Solution local_improve(Solution start) {
        vector<long long> cnt = start.cnt;
        long long usedM = start.usedM, usedL = start.usedL;
        long long bestVal = start.val;

        int maxPasses = 2; // keep small for time
        int Kremove = 8;

        for (int pass = 0; pass < maxPasses; ++pass) {
            bool improved = false;
            // prioritize items currently included
            vector<int> idxs(n);
            iota(idxs.begin(), idxs.end(), 0);
            sort(idxs.begin(), idxs.end(), [&](int a, int b){
                if (cnt[a] != cnt[b]) return cnt[a] > cnt[b];
                return items[a].v > items[b].v;
            });

            for (int ii = 0; ii < n; ++ii) {
                int i = idxs[ii];
                if (cnt[i] <= 0) continue;
                int maxK = (int)min<long long>(cnt[i], Kremove);
                for (int k = 1; k <= maxK; ++k) {
                    vector<long long> tmp = cnt;
                    tmp[i] -= k;
                    long long RM = usedM + k * items[i].m;
                    long long RL = usedL + k * items[i].l;
                    // Now refill
                    vector<double> alphas = {0.0, 0.5, 1.0};
                    long long bestLocalVal = -1;
                    vector<long long> bestLocalCnt;
                    for (double a : alphas) {
                        vector<long long> filled = greedy_refill(tmp, RM, RL, a);
                        Solution s = evaluate(filled);
                        if (s.val > bestLocalVal) {
                            bestLocalVal = s.val;
                            bestLocalCnt = move(filled);
                        }
                    }
                    if (bestLocalVal > bestVal) {
                        // accept
                        Solution s = evaluate(bestLocalCnt);
                        cnt = move(bestLocalCnt);
                        usedM = s.usedM; usedL = s.usedL; bestVal = s.val;
                        improved = true;
                        break;
                    }
                }
                if (improved) break;
            }
            if (!improved) break;
        }

        Solution res = evaluate(cnt);
        return res;
    }

    Solution solve() {
        vector<vector<long long>> candidates;
        candidates.reserve(64);

        // alpha-based greedy
        vector<double> alphas = {0.0, 0.1, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.7, 0.75, 0.8, 0.9, 1.0};
        for (double a : alphas) {
            auto order = sorted_by_ratio(a);
            candidates.push_back(fill_sorted_order(order));
            candidates.push_back(fill_incremental_static_ratio(a));
        }

        // max-norm
        auto ord_max = sorted_by_maxnorm();
        candidates.push_back(fill_sorted_order(ord_max));
        // dynamic incremental
        candidates.push_back(fill_incremental_dynamic_ratio());

        // Additional heuristics: sort by value desc
        {
            vector<int> order(n);
            iota(order.begin(), order.end(), 0);
            sort(order.begin(), order.end(), [&](int i, int j){
                if (items[i].v != items[j].v) return items[i].v > items[j].v;
                long long si = items[i].m + items[i].l, sj = items[j].m + items[j].l;
                return si < sj;
            });
            candidates.push_back(fill_sorted_order(order));
        }
        // sort by mass efficiency v/m
        {
            vector<pair<double,int>> arr;
            for (int i=0;i<n;++i){
                double eff = (items[i].m>0)? (double)items[i].v / (double)items[i].m : 1e300;
                arr.emplace_back(eff,i);
            }
            sort(arr.begin(), arr.end(), [&](auto&a, auto&b){
                if (a.first != b.first) return a.first > b.first;
                return items[a.second].v > items[b.second].v;
            });
            vector<int> order; order.reserve(n);
            for (auto &p:arr) order.push_back(p.second);
            candidates.push_back(fill_sorted_order(order));
        }
        // sort by volume efficiency v/l
        {
            vector<pair<double,int>> arr;
            for (int i=0;i<n;++i){
                double eff = (items[i].l>0)? (double)items[i].v / (double)items[i].l : 1e300;
                arr.emplace_back(eff,i);
            }
            sort(arr.begin(), arr.end(), [&](auto&a, auto&b){
                if (a.first != b.first) return a.first > b.first;
                return items[a.second].v > items[b.second].v;
            });
            vector<int> order; order.reserve(n);
            for (auto &p:arr) order.push_back(p.second);
            candidates.push_back(fill_sorted_order(order));
        }

        Solution best = best_of_candidates(candidates);

        // Local improvement
        best = local_improve(best);

        return best;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string input;
    {
        ostringstream oss;
        oss << cin.rdbuf();
        input = oss.str();
    }

    Parser parser(input);
    vector<Item> items = parser.parse();

    // Ensure exactly 12 categories; if not, proceed anyway
    HeuristicSolver solver(items);
    Solution best = solver.solve();

    // Output JSON with original keys and counts
    cout << "{\n";
    for (size_t i = 0; i < items.size(); ++i) {
        cout << " \"" << items[i].name << "\": " << (best.cnt.size() > i ? best.cnt[i] : 0);
        if (i + 1 < items.size()) cout << ",\n";
        else cout << "\n";
    }
    cout << "}\n";
    return 0;
}