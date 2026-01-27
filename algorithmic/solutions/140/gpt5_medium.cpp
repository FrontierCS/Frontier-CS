#include <bits/stdc++.h>
using namespace std;

static const long long COORD_LIMIT = 100000000LL;

struct Matcher {
    int k;
    vector<long long> U, V;
    vector<vector<long long>> dist; // dist[m][i * k + j] = distance for probe m between U[i] and V[j]
    vector<unordered_map<long long,int>> cnt; // counts for each probe m
    vector<vector<int>> adj; // candidate v's for each u based on support presence in all probes and parity
    vector<int> order; // order of u's for recursion
    vector<int> matchV; // assigned v index for each u
    vector<char> usedV;
    int mprobes;

    Matcher(int k): k(k), mprobes(0) {}

    static inline long long calcDistFromUV(long long u, long long v, long long sx, long long sy) {
        long long x = (u + v) / 2;
        long long y = (u - v) / 2;
        return llabs(x - sx) + llabs(y - sy);
    }

    void init(const vector<long long>& U_, const vector<long long>& V_, const vector<pair<long long,long long>>& probes, const vector<vector<long long>>& responses) {
        U = U_;
        V = V_;
        mprobes = (int)probes.size();
        dist.assign(mprobes, vector<long long>(k * k, 0));
        cnt.assign(mprobes, {});
        for (int m = 0; m < mprobes; ++m) {
            const auto& P = probes[m];
            for (int i = 0; i < k; ++i) {
                for (int j = 0; j < k; ++j) {
                    if ( ((U[i] + V[j]) & 1LL) != 0 ) {
                        dist[m][i * k + j] = LLONG_MIN; // invalid parity
                    } else {
                        dist[m][i * k + j] = calcDistFromUV(U[i], V[j], P.first, P.second);
                    }
                }
            }
            // build counts for this probe
            cnt[m].reserve(k*2+3);
            for (long long d : responses[m]) cnt[m][d]++;

        }
        // build adjacency based on parity and existence in all probes
        adj.assign(k, {});
        for (int i = 0; i < k; ++i) {
            for (int j = 0; j < k; ++j) {
                if ( ((U[i] + V[j]) & 1LL) != 0 ) continue; // parity mismatch
                bool ok = true;
                for (int m = 0; m < mprobes; ++m) {
                    long long d = dist[m][i * k + j];
                    if (d == LLONG_MIN) { ok = false; break; }
                    if (cnt[m].find(d) == cnt[m].end()) { ok = false; break; }
                }
                if (ok) adj[i].push_back(j);
            }
        }
        // order u's by increasing degree for better pruning
        order.resize(k);
        iota(order.begin(), order.end(), 0);
        sort(order.begin(), order.end(), [&](int a, int b){
            if (adj[a].size() != adj[b].size()) return adj[a].size() < adj[b].size();
            return a < b;
        });
        matchV.assign(k, -1);
        usedV.assign(k, 0);
    }

    bool dfs(int idx) {
        if (idx == k) return true;
        int u = order[idx];
        // try candidates for this u
        // sort candidates by some heuristic: fewer conflicts across probes? keep as is
        for (int v : adj[u]) {
            if (usedV[v]) continue;
            bool ok = true;
            // check counts for all probes
            vector<long long> dvals(mprobes);
            for (int m = 0; m < mprobes; ++m) {
                long long d = dist[m][u * k + v];
                dvals[m] = d;
                auto it = cnt[m].find(d);
                if (it == cnt[m].end() || it->second == 0) { ok = false; break; }
            }
            if (!ok) continue;
            // commit
            usedV[v] = 1;
            matchV[u] = v;
            for (int m = 0; m < mprobes; ++m) cnt[m][dvals[m]]--;
            if (dfs(idx + 1)) return true;
            // rollback
            for (int m = 0; m < mprobes; ++m) cnt[m][dvals[m]]++;
            matchV[u] = -1;
            usedV[v] = 0;
        }
        return false;
    }

    bool solve(vector<pair<long long,long long>>& outPts) {
        if (!dfs(0)) return false;
        outPts.clear();
        outPts.reserve(k);
        for (int i = 0; i < k; ++i) {
            int v = matchV[i];
            long long u = U[i], vv = V[v];
            long long x = (u + vv) / 2;
            long long y = (u - vv) / 2;
            outPts.emplace_back(x, y);
        }
        return true;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long b;
    int k, w;
    if (!(cin >> b >> k >> w)) {
        return 0;
    }

    auto query_single = [&](long long sx, long long sy) -> vector<long long> {
        cout << "? " << 1 << " " << sx << " " << sy << "\n";
        cout.flush();
        vector<long long> res(k);
        for (int i = 0; i < k; ++i) {
            long long d;
            if (!(cin >> d)) {
                // In case of I/O failure, just exit
                exit(0);
            }
            res[i] = d;
        }
        return res;
    };

    int waves_used = 0;

    // Wave 1: get U = x + y using (b, b)
    vector<long long> resp_bb = query_single(b, b); waves_used++;
    vector<long long> U(k);
    for (int i = 0; i < k; ++i) U[i] = 2*b - resp_bb[i];

    // Wave 2: get V = x - y using (b, -b)
    vector<long long> resp_bnb = query_single(b, -b); waves_used++;
    vector<long long> V(k);
    for (int i = 0; i < k; ++i) V[i] = 2*b - resp_bnb[i];

    // Now perform additional probes to match U to V
    vector<pair<long long,long long>> probePoints;
    vector<vector<long long>> probeResponses;

    auto add_probe = [&](long long sx, long long sy) {
        vector<long long> r = query_single(sx, sy);
        waves_used++;
        probePoints.emplace_back(sx, sy);
        probeResponses.push_back(r);
    };

    // Prepare a list of candidate probe points aimed to break symmetries
    vector<pair<long long,long long>> candidates;
    candidates.emplace_back(0, 0);
    candidates.emplace_back(b, 0);
    candidates.emplace_back(0, b);
    candidates.emplace_back(-b, 0);
    candidates.emplace_back(0, -b);
    candidates.emplace_back(b/2, 0);
    candidates.emplace_back(0, b/2);
    candidates.emplace_back(b, b/2);
    candidates.emplace_back(b/2, b);
    candidates.emplace_back(-b, b/2);
    candidates.emplace_back(b/2, -b);
    candidates.emplace_back(1, 0);
    candidates.emplace_back(0, 1);
    candidates.emplace_back(1, 1);
    candidates.emplace_back(b, 1);
    candidates.emplace_back(1, b);

    vector<pair<long long,long long>> solution;

    bool solved = false;
    for (size_t t = 0; t < candidates.size() && waves_used < w; ++t) {
        add_probe(candidates[t].first, candidates[t].second);
        // Try to solve with current probes
        Matcher matcher(k);
        matcher.init(U, V, probePoints, probeResponses);
        if (matcher.solve(solution)) {
            solved = true;
            break;
        }
    }

    if (!solved) {
        // As a fallback (should be rare), perform more generic probes until w exhausted or solved
        // Use additional arbitrary points that avoid corner linearization
        for (long long dx = 2; waves_used < w && !solved; ++dx) {
            long long sx = min(b, dx);
            long long sy = min(b, dx*dx % (2*b + 1));
            if (sx == b && sy == b) continue;
            add_probe(sx, sy);
            Matcher matcher(k);
            matcher.init(U, V, probePoints, probeResponses);
            if (matcher.solve(solution)) {
                solved = true;
                break;
            }
        }
    }

    if (!solved) {
        // As last resort, pair in sorted order (may be incorrect, but ensures output)
        vector<long long> Us = U, Vs = V;
        sort(Us.begin(), Us.end());
        sort(Vs.begin(), Vs.end());
        solution.clear();
        for (int i = 0; i < k; ++i) {
            long long u = Us[i], v = Vs[i];
            if ( ((u + v) & 1LL) != 0 ) {
                // fix parity by pairing next if possible
                bool fixed = false;
                for (int j = i+1; j < k; ++j) {
                    if ( ((Us[i] + Vs[j]) & 1LL) == 0 ) {
                        swap(Vs[i], Vs[j]);
                        v = Vs[i];
                        fixed = true;
                        break;
                    }
                }
                if (!fixed) {
                    // still bad, just coerce
                    v += 1;
                }
            }
            long long x = (u + v) / 2;
            long long y = (u - v) / 2;
            solution.emplace_back(x, y);
        }
    }

    cout << "! ";
    for (int i = 0; i < k; ++i) {
        cout << solution[i].first << " " << solution[i].second;
        if (i + 1 < k) cout << " ";
    }
    cout << "\n";
    cout.flush();
    return 0;
}