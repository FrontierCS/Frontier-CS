#include <bits/stdc++.h>
using namespace std;

static inline string trim(const string &s) {
    size_t b = s.find_first_not_of(" \t\r\n");
    if (b == string::npos) return "";
    size_t e = s.find_last_not_of(" \t\r\n");
    return s.substr(b, e - b + 1);
}

static inline vector<string> split_ws(const string &s) {
    vector<string> tok;
    string cur;
    for (char c : s) {
        if (isspace((unsigned char)c)) {
            if (!cur.empty()) { tok.push_back(cur); cur.clear(); }
        } else cur.push_back(c);
    }
    if (!cur.empty()) tok.push_back(cur);
    return tok;
}

struct Instance {
    double base = 0.0;
    int M = 0;
    vector<int> x;
    vector<vector<int>> ys;
    double D0 = 1.0, S0 = 1.0;
};

struct EvalResult {
    double cost = 1e300;
    vector<int> order;   // city indices 0..M-1
    vector<int> state;   // landing index per position in order (0-based)
};

static inline vector<int> rotate_to_min_n(const vector<int>& tour, const vector<int>& nPoints) {
    int M = (int)tour.size();
    int bestPos = 0;
    int bestN = nPoints[tour[0]];
    for (int i = 1; i < M; i++) {
        int nn = nPoints[tour[i]];
        if (nn < bestN) {
            bestN = nn;
            bestPos = i;
        }
    }
    vector<int> rot(M);
    for (int i = 0; i < M; i++) rot[i] = tour[(bestPos + i) % M];
    return rot;
}

static inline vector<int> rotate_to_lexicomin_by_min_city(const vector<int>& tour) {
    int M = (int)tour.size();
    int mn = *min_element(tour.begin(), tour.end());
    vector<int> best;
    bool init = false;
    for (int pos = 0; pos < M; pos++) {
        if (tour[pos] != mn) continue;
        vector<int> rot(M);
        for (int i = 0; i < M; i++) rot[i] = tour[(pos + i) % M];
        if (!init || rot < best) { best = move(rot); init = true; }
    }
    if (!init) return tour;
    return best;
}

static inline string canonical_key_cycle(const vector<int>& tour) {
    vector<int> t1 = rotate_to_lexicomin_by_min_city(tour);
    vector<int> rev = tour;
    reverse(rev.begin(), rev.end());
    vector<int> t2 = rotate_to_lexicomin_by_min_city(rev);
    const vector<int>& t = (t2 < t1) ? t2 : t1;
    string s;
    s.reserve(t.size() * 4);
    for (int i = 0; i < (int)t.size(); i++) {
        if (i) s.push_back(',');
        s += to_string(t[i]);
    }
    return s;
}

static Instance read_instance() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    Instance inst;
    string l1, l2;

    while (std::getline(cin, l1)) {
        l1 = trim(l1);
        if (!l1.empty()) break;
    }
    while (std::getline(cin, l2)) {
        l2 = trim(l2);
        if (!l2.empty()) break;
    }
    if (l1.empty()) return inst;

    vector<string> t1 = split_ws(l1);
    vector<string> t2 = split_ws(l2);

    bool use_rest_stream = false;
    string rest;

    if (t1.size() >= 2) {
        inst.base = stod(t1[0]);
        inst.M = stoi(t1[1]);
        use_rest_stream = true;
        rest = l2;
        rest.push_back('\n');
        rest.append((istreambuf_iterator<char>(cin)), istreambuf_iterator<char>());
    } else {
        if (t2.size() == 1) {
            inst.base = stod(t1[0]);
            inst.M = stoi(t2[0]);
            use_rest_stream = false;
        } else {
            // No explicit base; first line is M, second line is first city header
            inst.base = 0.0;
            inst.M = stoi(t1[0]);
            use_rest_stream = true;
            rest = l2;
            rest.push_back('\n');
            rest.append((istreambuf_iterator<char>(cin)), istreambuf_iterator<char>());
        }
    }

    inst.x.assign(inst.M, 0);
    inst.ys.assign(inst.M, {});

    auto parse_stream = [&](istream& in) {
        for (int i = 0; i < inst.M; i++) {
            int n, x;
            in >> n >> x;
            inst.x[i] = x;
            inst.ys[i].resize(n);
            for (int j = 0; j < n; j++) in >> inst.ys[i][j];
        }
        double D0, S0;
        in >> D0 >> S0;
        if (!in.fail()) {
            inst.D0 = D0;
            inst.S0 = S0;
        } else {
            inst.D0 = 1.0;
            inst.S0 = 1.0;
        }
    };

    if (use_rest_stream) {
        istringstream iss(rest);
        parse_stream(iss);
    } else {
        parse_stream(cin);
    }

    if (inst.D0 == 0) inst.D0 = 1.0;
    if (inst.S0 == 0) inst.S0 = 1.0;
    return inst;
}

static EvalResult evaluate_order_dp(
    const vector<int>& order,
    const vector<int>& x,
    const vector<vector<int>>& ys,
    const vector<vector<double>>& dx,
    const vector<vector<double>>& invdx,
    double wDist,
    double wSlope
) {
    const int M = (int)order.size();
    vector<int> nPoints(M);
    for (int i = 0; i < M; i++) nPoints[i] = (int)ys[order[i]].size();

    auto edgeCost = [&](int cityA, int idxA, int cityB, int idxB) -> double {
        double dxx = dx[cityA][cityB];
        double dy = (double)ys[cityB][idxB] - (double)ys[cityA][idxA];
        double dist = sqrt(dxx * dxx + dy * dy);
        double slope = (dy > 0.0) ? (dy * invdx[cityA][cityB]) : 0.0;
        return wDist * dist + wSlope * slope;
    };

    int startCity = order[0];
    int nStart = (int)ys[startCity].size();
    double bestTotal = 1e300;
    vector<int> bestState;

    for (int s0 = 0; s0 < nStart; s0++) {
        vector<double> dpPrev(nStart, 1e300);
        dpPrev[s0] = 0.0;

        vector<vector<int>> parent(M);
        parent[0].assign(nStart, -1);

        for (int pos = 1; pos < M; pos++) {
            int cPrev = order[pos - 1];
            int cCur = order[pos];
            int nPrev = (int)ys[cPrev].size();
            int nCur = (int)ys[cCur].size();

            vector<double> dpCur(nCur, 1e300);
            parent[pos].assign(nCur, -1);

            for (int s = 0; s < nCur; s++) {
                double best = 1e300;
                int arg = -1;
                for (int p = 0; p < nPrev; p++) {
                    double prevv = dpPrev[p];
                    if (prevv >= 1e290) continue;
                    double v = prevv + edgeCost(cPrev, p, cCur, s);
                    if (v < best) {
                        best = v;
                        arg = p;
                    }
                }
                dpCur[s] = best;
                parent[pos][s] = arg;
            }
            dpPrev.swap(dpCur);
        }

        int cLast = order[M - 1];
        int nLast = (int)ys[cLast].size();
        for (int sl = 0; sl < nLast; sl++) {
            double basev = dpPrev[sl];
            if (basev >= 1e290) continue;
            double total = basev + edgeCost(cLast, sl, startCity, s0);
            if (total < bestTotal) {
                bestTotal = total;
                vector<int> st(M, -1);
                st[M - 1] = sl;
                for (int pos = M - 1; pos >= 1; pos--) {
                    st[pos - 1] = parent[pos][st[pos]];
                    if (st[pos - 1] < 0) break;
                }
                st[0] = s0;
                bestState.swap(st);
            }
        }
    }

    EvalResult res;
    res.cost = bestTotal;
    res.order = order;
    res.state = bestState;
    return res;
}

static vector<int> nearest_neighbor_tour(int start, const vector<vector<double>>& costSym) {
    int M = (int)costSym.size();
    vector<int> tour;
    tour.reserve(M);
    vector<char> used(M, 0);
    int cur = start;
    used[cur] = 1;
    tour.push_back(cur);
    for (int step = 1; step < M; step++) {
        int best = -1;
        double bestC = 1e300;
        for (int j = 0; j < M; j++) if (!used[j]) {
            double c = costSym[cur][j];
            if (c < bestC) {
                bestC = c;
                best = j;
            }
        }
        if (best < 0) break;
        used[best] = 1;
        tour.push_back(best);
        cur = best;
    }
    return tour;
}

static vector<int> two_opt_first_improvement(vector<int> tour, const vector<vector<double>>& costSym) {
    int M = (int)tour.size();
    if (M < 4) return tour;
    int iter = 0;
    while (iter < 400) {
        bool improved = false;
        for (int i = 0; i < M; i++) {
            int a = tour[i];
            int b = tour[(i + 1) % M];
            for (int k = i + 2; k < M; k++) {
                if (i == 0 && k == M - 1) continue;
                int c = tour[k];
                int d = tour[(k + 1) % M];
                double before = costSym[a][b] + costSym[c][d];
                double after = costSym[a][c] + costSym[b][d];
                if (after + 1e-12 < before) {
                    reverse(tour.begin() + i + 1, tour.begin() + k + 1);
                    improved = true;
                    break;
                }
            }
            if (improved) break;
        }
        if (!improved) break;
        iter++;
    }
    return tour;
}

int main() {
    Instance inst = read_instance();
    int M = inst.M;
    if (M <= 0) return 0;

    const double k = 0.6;
    double wDist = (1.0 - k) / inst.D0;
    double wSlope = k / inst.S0;

    vector<int> nCity(M);
    for (int i = 0; i < M; i++) nCity[i] = (int)inst.ys[i].size();

    // Representative y: median
    vector<double> repY(M, 0.0);
    for (int i = 0; i < M; i++) {
        auto v = inst.ys[i];
        sort(v.begin(), v.end());
        repY[i] = (double)v[v.size() / 2];
    }

    // Precompute dx and invdx
    vector<vector<double>> dx(M, vector<double>(M, 0.0));
    vector<vector<double>> invdx(M, vector<double>(M, 0.0));
    for (int i = 0; i < M; i++) for (int j = 0; j < M; j++) {
        double d = (double)abs(inst.x[i] - inst.x[j]);
        dx[i][j] = d;
        invdx[i][j] = 1.0 / max(d, 1e-6);
    }

    // Symmetric approximation cost matrix for order heuristics
    vector<vector<double>> costSym(M, vector<double>(M, 0.0));
    for (int i = 0; i < M; i++) for (int j = 0; j < M; j++) {
        if (i == j) { costSym[i][j] = 0.0; continue; }
        double dxx = dx[i][j];
        double dy = repY[j] - repY[i];
        double dist = sqrt(dxx * dxx + dy * dy);
        double slopeSym = fabs(dy) * invdx[i][j];
        costSym[i][j] = wDist * dist + wSlope * slopeSym;
    }

    vector<vector<int>> candidates;

    // Candidate: sort by x
    vector<int> idx(M);
    iota(idx.begin(), idx.end(), 0);
    stable_sort(idx.begin(), idx.end(), [&](int a, int b) {
        if (inst.x[a] != inst.x[b]) return inst.x[a] < inst.x[b];
        return repY[a] < repY[b];
    });
    candidates.push_back(idx);
    vector<int> idxRev = idx;
    reverse(idxRev.begin(), idxRev.end());
    candidates.push_back(idxRev);

    // Nearest neighbor with various starts
    vector<int> starts;
    starts.push_back(0);
    starts.push_back(M / 2);
    starts.push_back(M - 1);

    int minX = 0, maxX = 0;
    for (int i = 1; i < M; i++) {
        if (inst.x[i] < inst.x[minX]) minX = i;
        if (inst.x[i] > inst.x[maxX]) maxX = i;
    }
    starts.push_back(minX);
    starts.push_back(maxX);

    int minY = 0, maxY = 0;
    for (int i = 1; i < M; i++) {
        if (repY[i] < repY[minY]) minY = i;
        if (repY[i] > repY[maxY]) maxY = i;
    }
    starts.push_back(minY);
    starts.push_back(maxY);

    mt19937 rng(1234567);
    uniform_int_distribution<int> uid(0, M - 1);
    for (int t = 0; t < 4; t++) starts.push_back(uid(rng));

    for (int s : starts) {
        auto tour = nearest_neighbor_tour(s, costSym);
        tour = two_opt_first_improvement(move(tour), costSym);
        candidates.push_back(tour);
    }

    // Deduplicate (cycle-wise) and evaluate
    unordered_set<string> seen;
    EvalResult best;

    vector<int> nPointsPerCity = nCity;

    for (auto &tour0 : candidates) {
        if ((int)tour0.size() != M) continue;

        for (int revFlag = 0; revFlag < 2; revFlag++) {
            vector<int> tour = tour0;
            if (revFlag) reverse(tour.begin(), tour.end());

            // Rotate to start at a city with minimal number of landing points (for faster DP)
            tour = rotate_to_min_n(tour, nPointsPerCity);

            string key = canonical_key_cycle(tour);
            if (seen.find(key) != seen.end()) continue;
            seen.insert(key);

            EvalResult cur = evaluate_order_dp(tour, inst.x, inst.ys, dx, invdx, wDist, wSlope);
            if (cur.cost < best.cost) best = move(cur);
        }
    }

    // Fallback if something went wrong
    if (best.order.empty()) {
        best.order = idx;
        best = evaluate_order_dp(best.order, inst.x, inst.ys, dx, invdx, wDist, wSlope);
    }

    // Output
    for (int i = 0; i < M; i++) {
        if (i) cout << "@";
        int city = best.order[i];
        int lp = (best.state.empty() ? 0 : best.state[i]);
        cout << "(" << (city + 1) << "," << (lp + 1) << ")";
    }
    cout << "\n";
    return 0;
}