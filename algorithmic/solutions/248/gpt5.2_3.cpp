#include <bits/stdc++.h>
using namespace std;

struct City {
    int id; // 0-based input id
    int x;
    vector<int> y;
    double yRep;
};

static inline vector<string> splitTokens(const string& s) {
    vector<string> t;
    string w;
    stringstream ss(s);
    while (ss >> w) t.push_back(w);
    return t;
}

static inline bool isBlankLine(const string& s) {
    for (char c : s) if (!isspace((unsigned char)c)) return false;
    return true;
}

static inline double directedCost(int xi, int yi, int xj, int yj, double Dcoef, double Scoef) {
    double dx = (double)xj - (double)xi;
    double dy = (double)yj - (double)yi;
    double dist = hypot(dx, dy);
    double adx = fabs(dx);
    double slope = 0.0;
    if (dy > 0) {
        if (adx < 1e-12) slope = 1e9;
        else slope = dy / adx;
    }
    return Dcoef * dist + Scoef * slope;
}

static inline double symProxyCost(int xi, double yi, int xj, double yj, double Dcoef, double Scoef) {
    double dx = (double)xj - (double)xi;
    double dy = (double)yj - (double)yi;
    double dist = hypot(dx, dy);
    double adx = fabs(dx);
    double slopeAbs = 0.0;
    if (adx < 1e-12) {
        slopeAbs = (fabs(dy) > 1e-12) ? 1e9 : 0.0;
    } else {
        slopeAbs = fabs(dy) / adx;
    }
    return Dcoef * dist + Scoef * slopeAbs;
}

static vector<int> buildNearestNeighborTour(int start, const vector<vector<double>>& w) {
    int M = (int)w.size();
    vector<int> tour;
    tour.reserve(M);
    vector<char> used(M, 0);
    int cur = start;
    used[cur] = 1;
    tour.push_back(cur);
    for (int step = 1; step < M; step++) {
        int best = -1;
        double bestW = 1e300;
        for (int j = 0; j < M; j++) if (!used[j]) {
            double c = w[cur][j];
            if (c < bestW) {
                bestW = c;
                best = j;
            }
        }
        if (best == -1) break;
        used[best] = 1;
        tour.push_back(best);
        cur = best;
    }
    return tour;
}

static void rotateToCity(vector<int>& tour, int cityId0) {
    int M = (int)tour.size();
    int pos = -1;
    for (int i = 0; i < M; i++) if (tour[i] == cityId0) { pos = i; break; }
    if (pos > 0) rotate(tour.begin(), tour.begin() + pos, tour.end());
}

static void twoOptFirstImprovement(vector<int>& tour, const vector<vector<double>>& w, int maxSwaps = 20000) {
    int M = (int)tour.size();
    if (M <= 3) return;

    int swaps = 0;
    while (swaps < maxSwaps) {
        bool improved = false;
        for (int i = 0; i < M; i++) {
            int a = tour[i];
            int b = tour[(i + 1) % M];
            for (int j = i + 2; j < M; j++) {
                if (i == 0 && j == M - 1) continue;
                int c = tour[j];
                int d = tour[(j + 1) % M];

                double delta = (w[a][c] + w[b][d]) - (w[a][b] + w[c][d]);
                if (delta < -1e-12) {
                    reverse(tour.begin() + (i + 1), tour.begin() + (j + 1));
                    improved = true;
                    swaps++;
                    break;
                }
            }
            if (improved || swaps >= maxSwaps) break;
        }
        if (!improved) break;
    }
}

struct DPResult {
    double cost;
    vector<int> state; // per tour position: landing index (0-based)
};

static DPResult optimizeLandingsForTour(
    const vector<int>& tour,
    const vector<City>& cities,
    double Dcoef, double Scoef
) {
    int M = (int)tour.size();
    vector<int> nOpt(M);
    for (int p = 0; p < M; p++) nOpt[p] = (int)cities[tour[p]].y.size();

    vector<vector<double>> edgeCost(M - 1);
    for (int p = 0; p < M - 1; p++) {
        int ci = tour[p], cj = tour[p + 1];
        int ni = nOpt[p], nj = nOpt[p + 1];
        edgeCost[p].assign((size_t)ni * (size_t)nj, 0.0);
        for (int si = 0; si < ni; si++) {
            int yi = cities[ci].y[si];
            for (int tj = 0; tj < nj; tj++) {
                int yj = cities[cj].y[tj];
                edgeCost[p][(size_t)si * (size_t)nj + (size_t)tj] =
                    directedCost(cities[ci].x, yi, cities[cj].x, yj, Dcoef, Scoef);
            }
        }
    }

    vector<double> closeCost;
    {
        int cl = tour[M - 1], c0 = tour[0];
        int nl = nOpt[M - 1], n0 = nOpt[0];
        closeCost.assign((size_t)nl * (size_t)n0, 0.0);
        for (int sl = 0; sl < nl; sl++) {
            int yl = cities[cl].y[sl];
            for (int t0 = 0; t0 < n0; t0++) {
                int y0 = cities[c0].y[t0];
                closeCost[(size_t)sl * (size_t)n0 + (size_t)t0] =
                    directedCost(cities[cl].x, yl, cities[c0].x, y0, Dcoef, Scoef);
            }
        }
    }

    int n0 = nOpt[0];
    double bestTotal = 1e300;
    int bestS0 = 0, bestLast = 0;
    vector<vector<int>> bestPar;

    for (int s0 = 0; s0 < n0; s0++) {
        vector<vector<int>> par(M);
        for (int p = 0; p < M; p++) par[p].assign(nOpt[p], -1);

        vector<double> dpPrev(nOpt[0], 1e300);
        dpPrev[s0] = 0.0;

        for (int p = 0; p < M - 1; p++) {
            int ni = nOpt[p], nj = nOpt[p + 1];
            vector<double> dpNext(nj, 1e300);
            const auto& mat = edgeCost[p];

            for (int tj = 0; tj < nj; tj++) {
                double best = 1e300;
                int arg = -1;
                for (int si = 0; si < ni; si++) {
                    double v = dpPrev[si] + mat[(size_t)si * (size_t)nj + (size_t)tj];
                    if (v < best) {
                        best = v;
                        arg = si;
                    }
                }
                dpNext[tj] = best;
                par[p + 1][tj] = arg;
            }
            dpPrev.swap(dpNext);
        }

        int nl = nOpt[M - 1];
        for (int sl = 0; sl < nl; sl++) {
            double total = dpPrev[sl] + closeCost[(size_t)sl * (size_t)n0 + (size_t)s0];
            if (total < bestTotal) {
                bestTotal = total;
                bestS0 = s0;
                bestLast = sl;
                bestPar = par;
            }
        }
    }

    vector<int> state(M, 0);
    state[0] = bestS0;
    state[M - 1] = bestLast;
    for (int p = M - 1; p >= 1; p--) {
        int prev = bestPar[p][state[p]];
        if (prev < 0) prev = 0;
        state[p - 1] = prev;
    }

    return {bestTotal, state};
}

static vector<vector<double>> buildSymMatrixFromY(const vector<City>& cities, const vector<double>& yVal, double Dcoef, double Scoef) {
    int M = (int)cities.size();
    vector<vector<double>> w(M, vector<double>(M, 0.0));
    for (int i = 0; i < M; i++) {
        w[i][i] = 0.0;
        for (int j = i + 1; j < M; j++) {
            double c = symProxyCost(cities[i].x, yVal[i], cities[j].x, yVal[j], Dcoef, Scoef);
            w[i][j] = w[j][i] = c;
        }
    }
    return w;
}

struct ParsedInput {
    double base = 0.0;
    int M = 0;
    vector<City> cities;
    int Dorig = 1, Sorig = 1;
};

static bool parseFromLines(const vector<string>& linesAfterBase, ParsedInput& out) {
    if (linesAfterBase.empty()) return false;

    auto tok0 = splitTokens(linesAfterBase[0]);
    if (tok0.empty()) return false;

    // Case 1: M is provided on its own line (single token)
    if ((int)tok0.size() == 1) {
        int M = stoi(tok0[0]);
        if (M < 2 || M > 200) return false;
        if ((int)linesAfterBase.size() != 2 * M + 2) return false; // M line + 2M city lines + DS line

        vector<City> cities;
        cities.reserve(M);
        int idx = 1;
        for (int i = 0; i < M; i++) {
            auto head = splitTokens(linesAfterBase[idx++]);
            if ((int)head.size() < 2) return false;
            int n = stoi(head[0]);
            int x = stoi(head[1]);
            if (n < 1 || n > 20) return false;

            auto ys = splitTokens(linesAfterBase[idx++]);
            if ((int)ys.size() != n) return false;
            City c;
            c.id = i;
            c.x = x;
            c.y.resize(n);
            for (int k = 0; k < n; k++) c.y[k] = stoi(ys[k]);
            cities.push_back(move(c));
        }

        auto ds = splitTokens(linesAfterBase[idx++]);
        if ((int)ds.size() < 2) return false;
        out.M = M;
        out.cities = move(cities);
        out.Dorig = stoi(ds[0]);
        out.Sorig = stoi(ds[1]);
        return true;
    }

    // Case 2: M not provided; remaining lines are 2*M city lines + DS line
    int L = (int)linesAfterBase.size();
    if (L < 3) return false;
    if ((L - 1) % 2 != 0) return false;
    int M = (L - 1) / 2;
    if (M < 2 || M > 200) return false;

    vector<City> cities;
    cities.reserve(M);
    int idx = 0;
    for (int i = 0; i < M; i++) {
        auto head = splitTokens(linesAfterBase[idx++]);
        if ((int)head.size() < 2) return false;
        int n = stoi(head[0]);
        int x = stoi(head[1]);
        if (n < 1 || n > 20) return false;

        auto ys = splitTokens(linesAfterBase[idx++]);
        if ((int)ys.size() != n) return false;
        City c;
        c.id = i;
        c.x = x;
        c.y.resize(n);
        for (int k = 0; k < n; k++) c.y[k] = stoi(ys[k]);
        cities.push_back(move(c));
    }
    auto ds = splitTokens(linesAfterBase[idx++]);
    if ((int)ds.size() < 2) return false;

    out.M = M;
    out.cities = move(cities);
    out.Dorig = stoi(ds[0]);
    out.Sorig = stoi(ds[1]);
    return true;
}

static bool parseFromTokens(const vector<string>& tokens, ParsedInput& out) {
    if (tokens.size() < 6) return false;
    out.base = stod(tokens[0]);

    auto tryParseWithM = [&](int M, size_t posStart, vector<City>& cities, int& Dorig, int& Sorig) -> bool {
        if (M < 2 || M > 200) return false;
        size_t pos = posStart;
        cities.clear();
        cities.reserve(M);
        for (int i = 0; i < M; i++) {
            if (pos + 2 > tokens.size()) return false;
            int n = stoi(tokens[pos++]);
            int x = stoi(tokens[pos++]);
            if (n < 1 || n > 20) return false;
            if (pos + (size_t)n > tokens.size()) return false;
            City c;
            c.id = i;
            c.x = x;
            c.y.resize(n);
            for (int k = 0; k < n; k++) c.y[k] = stoi(tokens[pos++]);
            cities.push_back(move(c));
        }
        if (pos + 2 != tokens.size()) return false;
        Dorig = stoi(tokens[pos++]);
        Sorig = stoi(tokens[pos++]);
        return true;
    };

    auto tryParseNoM = [&](vector<City>& cities, int& Dorig, int& Sorig) -> bool {
        size_t pos = 1;
        cities.clear();
        int id = 0;
        while (pos + 2 < tokens.size()) {
            if (pos + 2 > tokens.size() - 2) return false;
            int n = stoi(tokens[pos++]);
            int x = stoi(tokens[pos++]);
            if (n < 1 || n > 20) return false;
            if (pos + (size_t)n > tokens.size() - 2) return false;
            City c;
            c.id = id++;
            c.x = x;
            c.y.resize(n);
            for (int k = 0; k < n; k++) c.y[k] = stoi(tokens[pos++]);
            cities.push_back(move(c));
            if (id > 200) return false;
            if (pos == tokens.size() - 2) break;
        }
        if (pos + 2 != tokens.size()) return false;
        Dorig = stoi(tokens[pos++]);
        Sorig = stoi(tokens[pos++]);
        if ((int)cities.size() < 2 || (int)cities.size() > 200) return false;
        return true;
    };

    vector<City> c1, c2;
    int D1=0,S1=0,D2=0,S2=0;
    bool okWithM = false, okNoM = false;

    if (tokens.size() >= 2) {
        int Mguess = stoi(tokens[1]);
        okWithM = tryParseWithM(Mguess, 2, c1, D1, S1);
    }
    okNoM = tryParseNoM(c2, D2, S2);

    if (okWithM && !okNoM) {
        out.M = (int)c1.size();
        out.cities = move(c1);
        out.Dorig = D1; out.Sorig = S1;
        return true;
    }
    if (!okWithM && okNoM) {
        out.M = (int)c2.size();
        out.cities = move(c2);
        out.Dorig = D2; out.Sorig = S2;
        return true;
    }
    if (okWithM && okNoM) {
        // Disambiguate: if tokens[1] > 20, it's almost surely M (since n<=20)
        if (stoi(tokens[1]) > 20) {
            out.M = (int)c1.size();
            out.cities = move(c1);
            out.Dorig = D1; out.Sorig = S1;
        } else {
            // Prefer no-M variant to match possible input format like the sample.
            out.M = (int)c2.size();
            out.cities = move(c2);
            out.Dorig = D2; out.Sorig = S2;
        }
        return true;
    }
    return false;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string baseLine;
    while (std::getline(cin, baseLine)) {
        if (!isBlankLine(baseLine)) break;
    }
    if (baseLine.empty()) return 0;

    ParsedInput inp;
    inp.base = stod(splitTokens(baseLine)[0]);

    vector<string> linesAfterBase;
    string line;
    while (std::getline(cin, line)) {
        if (isBlankLine(line)) continue;
        linesAfterBase.push_back(line);
    }

    bool ok = parseFromLines(linesAfterBase, inp);
    if (!ok) {
        // Fallback to token parsing
        vector<string> tokens;
        {
            auto t0 = splitTokens(baseLine);
            tokens.insert(tokens.end(), t0.begin(), t0.end());
            for (auto& ln : linesAfterBase) {
                auto tt = splitTokens(ln);
                tokens.insert(tokens.end(), tt.begin(), tt.end());
            }
        }
        ok = parseFromTokens(tokens, inp);
        if (!ok) return 0;
    }

    int M = inp.M;
    vector<City> cities = move(inp.cities);
    int Dorig = inp.Dorig;
    int Sorig = inp.Sorig;

    // Representative y: median
    for (auto& c : cities) {
        vector<int> tmp = c.y;
        nth_element(tmp.begin(), tmp.begin() + (int)tmp.size() / 2, tmp.end());
        c.yRep = (double)tmp[tmp.size() / 2];
    }

    const double k = 0.6;
    double Dcoef = (1.0 - k) / (double)max(1, Dorig);
    double Scoef = k / (double)max(1, Sorig);

    // Initial symmetric proxy matrix using yRep
    vector<double> yValRep(M);
    for (int i = 0; i < M; i++) yValRep[i] = cities[i].yRep;
    auto wRep = buildSymMatrixFromY(cities, yValRep, Dcoef, Scoef);

    // Candidate tours
    vector<vector<int>> candidates;

    // x-sorted
    {
        vector<int> t(M);
        iota(t.begin(), t.end(), 0);
        stable_sort(t.begin(), t.end(), [&](int a, int b) {
            if (cities[a].x != cities[b].x) return cities[a].x < cities[b].x;
            return cities[a].yRep < cities[b].yRep;
        });
        candidates.push_back(t);
    }

    // nearest neighbor starts
    {
        int minx = 0, maxx = 0;
        for (int i = 1; i < M; i++) {
            if (cities[i].x < cities[minx].x) minx = i;
            if (cities[i].x > cities[maxx].x) maxx = i;
        }
        candidates.push_back(buildNearestNeighborTour(0, wRep));
        if (minx != 0) candidates.push_back(buildNearestNeighborTour(minx, wRep));
        if (maxx != 0 && maxx != minx) candidates.push_back(buildNearestNeighborTour(maxx, wRep));

        std::mt19937_64 rng(1234567);
        for (int r = 0; r < 2; r++) {
            int st = (int)(rng() % (uint64_t)M);
            candidates.push_back(buildNearestNeighborTour(st, wRep));
        }
    }

    // Evaluate candidates: 2-opt on wRep, then DP on true cost
    double bestCost = 1e300;
    vector<int> bestTour;
    vector<int> bestState;

    for (auto tour : candidates) {
        if ((int)tour.size() != M) continue;
        twoOptFirstImprovement(tour, wRep, 20000);
        rotateToCity(tour, 0);
        auto res = optimizeLandingsForTour(tour, cities, Dcoef, Scoef);
        if (res.cost < bestCost) {
            bestCost = res.cost;
            bestTour = move(tour);
            bestState = move(res.state);
        }
    }

    if (bestTour.empty()) {
        bestTour.resize(M);
        iota(bestTour.begin(), bestTour.end(), 0);
        rotateToCity(bestTour, 0);
        auto res = optimizeLandingsForTour(bestTour, cities, Dcoef, Scoef);
        bestCost = res.cost;
        bestState = move(res.state);
    }

    // Refinement loop: build symmetric matrix from chosen y, run 2-opt, re-optimize landing points
    for (int it = 0; it < 5; it++) {
        vector<double> yChosen(M, 0.0);
        for (int p = 0; p < M; p++) {
            int cid = bestTour[p];
            yChosen[cid] = (double)cities[cid].y[bestState[p]];
        }
        auto wChosen = buildSymMatrixFromY(cities, yChosen, Dcoef, Scoef);

        auto tour2 = bestTour;
        twoOptFirstImprovement(tour2, wChosen, 20000);
        rotateToCity(tour2, 0);

        auto res2 = optimizeLandingsForTour(tour2, cities, Dcoef, Scoef);
        if (res2.cost + 1e-12 < bestCost) {
            bestCost = res2.cost;
            bestTour = move(tour2);
            bestState = move(res2.state);
        } else {
            break;
        }
    }

    // Output
    for (int p = 0; p < M; p++) {
        if (p) cout << "@";
        cout << "(" << (bestTour[p] + 1) << "," << (bestState[p] + 1) << ")";
    }
    return 0;
}