#include <bits/stdc++.h>
using namespace std;

struct City {
    int id; // original id (1-based)
    double x;
    vector<double> ys;
};

static vector<long long> parseInts(const string &s) {
    vector<long long> res;
    stringstream ss(s);
    long long v;
    while (ss >> v) res.push_back(v);
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Read entire input as lines
    vector<string> lines;
    {
        string line;
        while (getline(cin, line)) {
            // keep even empty lines? We'll skip empty to be robust
            // but for safety, include only non-empty lines
            // If an empty line exists, it shouldn't affect parsing
            if (!line.empty())
                lines.push_back(line);
        }
    }
    if (lines.empty()) {
        return 0;
    }

    // Parse base from first non-empty line
    double base = 0.0;
    {
        string s = lines[0];
        // base might be real number
        try {
            base = stod(s);
        } catch (...) {
            // if parsing fails, try to get first token
            auto toks = parseInts(s);
            if (!toks.empty()) base = toks[0];
        }
    }

    // Now parse the rest
    vector<City> cities;
    double Dnorm = 1.0, Snorm = 1.0; // normalization denominators
    const double K = 0.6;

    if (lines.size() >= 2) {
        // Check if second line contains only M or already city data (n x)
        auto tokens = parseInts(lines[1]);
        if (tokens.size() == 1) {
            // Format with explicit M
            int M = (int)tokens[0];
            int expectedLines = 1 + 1 + 2*M + 1; // base + M-line + city-lines + D S
            int idx = 2;
            cities.reserve(M);
            for (int i = 0; i < M && idx + 1 < (int)lines.size(); ++i) {
                auto nx = parseInts(lines[idx++]);
                if (nx.size() < 2) {
                    // malformed, try to continue
                    nx.resize(2, 0);
                }
                int n = (int)nx[0];
                double x = (double)nx[1];

                vector<long long> ys_ll;
                if (idx < (int)lines.size()) {
                    ys_ll = parseInts(lines[idx++]);
                }
                vector<double> ys;
                ys.reserve(n);
                for (int j = 0; j < n && j < (int)ys_ll.size(); ++j) ys.push_back((double)ys_ll[j]);
                // if less than n provided, pad zeros
                while ((int)ys.size() < n) ys.push_back(0.0);

                City c;
                c.id = i + 1;
                c.x = x;
                c.ys = move(ys);
                cities.push_back(move(c));
            }
            // Remaining line for D S (use last available line that has at least 1 token)
            for (int i = (int)lines.size() - 1; i >= 0; --i) {
                auto ds = parseInts(lines[i]);
                if (ds.size() >= 2) {
                    Dnorm = (double)ds[0];
                    Snorm = (double)ds[1];
                    break;
                }
            }
        } else {
            // Format without explicit M; parse pairs of (n x) and y-line until last line (D S)
            int L = (int)lines.size();
            int idx = 1;
            vector<pair<int,double>> nx_list;
            vector<vector<double>> ys_list;
            while (idx + 1 < L) {
                auto nx = parseInts(lines[idx]);
                if (idx + 1 >= L) break;
                auto ys_ll = parseInts(lines[idx + 1]);
                if (nx.size() < 2) break;
                int n = (int)nx[0];
                double x = (double)nx[1];
                vector<double> ys;
                ys.reserve(n);
                for (int j = 0; j < n && j < (int)ys_ll.size(); ++j) ys.push_back((double)ys_ll[j]);
                while ((int)ys.size() < n) ys.push_back(0.0);

                nx_list.emplace_back(n, x);
                ys_list.emplace_back(move(ys));

                idx += 2;
                // Stop if only one line left (assume it's D S)
                if (idx >= L - 1) break;
            }
            int M = (int)nx_list.size();
            cities.reserve(M);
            for (int i = 0; i < M; ++i) {
                City c;
                c.id = i + 1;
                c.x = nx_list[i].second;
                c.ys = move(ys_list[i]);
                cities.push_back(move(c));
            }
            // Last line should be D S
            if (!lines.empty()) {
                auto ds = parseInts(lines.back());
                if (ds.size() >= 2) {
                    Dnorm = (double)ds[0];
                    Snorm = (double)ds[1];
                }
            }
        }
    } else {
        // Only base line present; nothing to do
        return 0;
    }

    int M = (int)cities.size();
    if (M == 0) {
        return 0;
    }

    // Prepare order indices sorted by x ascending
    vector<int> ordAsc(M), ordDesc(M);
    iota(ordAsc.begin(), ordAsc.end(), 0);
    stable_sort(ordAsc.begin(), ordAsc.end(), [&](int a, int b) {
        if (cities[a].x != cities[b].x) return cities[a].x < cities[b].x;
        return cities[a].id < cities[b].id;
    });
    ordDesc = ordAsc;
    reverse(ordDesc.begin(), ordDesc.end());

    auto buildSeq = [&](const vector<int>& ord) {
        vector<City> seq;
        seq.reserve(M);
        for (int idx : ord) seq.push_back(cities[idx]);
        return seq;
    };

    const double HUGE_SLOPE = 1e12;

    auto edgeCost = [&](double x1, double y1, double x2, double y2) -> double {
        double dx = x2 - x1;
        double dy = y2 - y1;
        double dist = hypot(dx, dy);
        double hdist = fabs(dx);
        double slope = 0.0;
        if (dy > 0) {
            if (hdist == 0.0) slope = HUGE_SLOPE;
            else slope = dy / hdist;
        }
        double cost = (1.0 - K) * (dist / max(1e-12, Dnorm)) + K * (slope / max(1e-12, Snorm));
        return cost;
    };

    struct Result {
        double cost;
        vector<int> yIdx; // per city in order, 0-based index of landing point
        vector<int> ord;  // indices of cities in original order
    };

    auto solveForOrder = [&](const vector<int>& ord) -> Result {
        vector<City> seq = buildSeq(ord);
        int N = (int)seq.size();
        vector<int> ni(N);
        for (int i = 0; i < N; ++i) ni[i] = (int)seq[i].ys.size();

        // Precompute edge costs between consecutive cities
        vector<vector<vector<double>>> edge(N - 1);
        for (int i = 0; i < N - 1; ++i) {
            int aN = ni[i], bN = ni[i+1];
            edge[i].assign(aN, vector<double>(bN, 0.0));
            for (int a = 0; a < aN; ++a) {
                for (int b = 0; b < bN; ++b) {
                    edge[i][a][b] = edgeCost(seq[i].x, seq[i].ys[a], seq[i+1].x, seq[i+1].ys[b]);
                }
            }
        }
        // Closure edge from last to first
        vector<vector<double>> edgeLast(ni[N-1], vector<double>(ni[0], 0.0));
        for (int a = 0; a < ni[N-1]; ++a) {
            for (int b = 0; b < ni[0]; ++b) {
                edgeLast[a][b] = edgeCost(seq[N-1].x, seq[N-1].ys[a], seq[0].x, seq[0].ys[b]);
            }
        }

        const double INF = 1e300;
        double bestCost = INF;
        vector<int> bestSel;
        // DP per starting choice at first city
        for (int startY = 0; startY < ni[0]; ++startY) {
            vector<double> cur(ni[0], INF);
            cur[startY] = 0.0;

            // To reconstruct path, store predecessors for each layer
            vector<vector<int>> prevIdx(N); // prevIdx[i][k] = index at city i-1 leading to k at city i
            for (int i = 0; i < N - 1; ++i) {
                vector<double> nxt(ni[i+1], INF);
                vector<int> prev(ni[i+1], -1);
                for (int a = 0; a < ni[i]; ++a) {
                    double ca = cur[a];
                    if (ca >= INF/2) continue;
                    for (int b = 0; b < ni[i+1]; ++b) {
                        double val = ca + edge[i][a][b];
                        if (val < nxt[b]) {
                            nxt[b] = val;
                            prev[b] = a;
                        }
                    }
                }
                prevIdx[i+1] = move(prev);
                cur = move(nxt);
            }

            for (int lastY = 0; lastY < ni[N-1]; ++lastY) {
                double total = cur[lastY] + edgeLast[lastY][startY];
                if (total < bestCost) {
                    bestCost = total;
                    // Reconstruct
                    vector<int> sel(N, -1);
                    sel[0] = startY;
                    sel[N-1] = lastY;
                    for (int i = N - 1; i >= 1; --i) {
                        int p = prevIdx[i][sel[i]];
                        sel[i-1] = p;
                    }
                    bestSel = move(sel);
                }
            }
        }

        Result res;
        res.cost = bestCost;
        res.yIdx = bestSel;
        res.ord = ord;
        return res;
    };

    Result resA = solveForOrder(ordAsc);
    Result resB = solveForOrder(ordDesc);
    Result best = (resA.cost <= resB.cost ? resA : resB);

    // Output in required format: (city_id, landing_point_index) joined by "@"
    // city_id is original id (1-based)
    // landing_point_index is 1-based index in that city's terminal
    // best.ord maps order position to original city index
    vector<pair<int,int>> outputPairs;
    outputPairs.reserve(M);
    for (int i = 0; i < M; ++i) {
        int cityIdx = best.ord[i];
        int yIndex = best.yIdx[i]; // 0-based
        outputPairs.emplace_back(cities[cityIdx].id, yIndex + 1);
    }

    for (int i = 0; i < M; ++i) {
        if (i) cout << "@";
        cout << "(" << outputPairs[i].first << "," << outputPairs[i].second << ")";
    }
    cout << "\n";
    return 0;
}