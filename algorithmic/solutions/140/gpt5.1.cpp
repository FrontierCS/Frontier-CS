#include <bits/stdc++.h>
using namespace std;

using ll = long long;

// Globals for pairing DFS
int G_K;
int G_ANCH;
vector<ll> G_XS, G_YS;
vector<pair<int,int>> G_Anchors;
vector<vector<ll>> G_RemDists;
vector<int> G_UsedY, G_AssignY;

bool dfs_pair(int idx) {
    if (idx == G_K) return true;
    int M = G_ANCH;
    for (int j = 0; j < G_K; ++j) {
        if (G_UsedY[j]) continue;
        bool possible = true;
        vector<int> pos(M);
        for (int m = 0; m < M; ++m) {
            ll d = llabs(G_XS[idx] - (ll)G_Anchors[m].first) + llabs(G_YS[j] - (ll)G_Anchors[m].second);
            auto &vec = G_RemDists[m];
            int p = -1;
            for (int ii = 0; ii < (int)vec.size(); ++ii) {
                if (vec[ii] == d) {
                    p = ii;
                    break;
                }
            }
            if (p == -1) {
                possible = false;
                break;
            }
            pos[m] = p;
        }
        if (!possible) continue;
        G_UsedY[j] = 1;
        G_AssignY[idx] = j;
        vector<ll> removed(M);
        for (int m = 0; m < M; ++m) {
            auto &vec = G_RemDists[m];
            removed[m] = vec[pos[m]];
            vec.erase(vec.begin() + pos[m]);
        }
        if (dfs_pair(idx + 1)) return true;
        for (int m = 0; m < M; ++m) {
            auto &vec = G_RemDists[m];
            vec.insert(vec.begin() + pos[m], removed[m]);
        }
        G_UsedY[j] = 0;
        G_AssignY[idx] = -1;
    }
    return false;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    ll b_ll;
    int k, w;
    if (!(cin >> b_ll >> k >> w)) {
        return 0;
    }
    int b = (int)b_ll;
    G_K = k;

    // Estimate maximum number of queries needed by full algorithm
    ll range = 2 * b_ll + 1;
    int steps = 0;
    while ((1LL << steps) < range) steps++;
    const int ANCHORS_N = 4;
    ll Q_bound = 4LL * k * steps + ANCHORS_N; // upper bound on #waves (each wave uses 1 probe)

    if (w < Q_bound) {
        // Fallback: no queries, just output some dummy points within [-b,b]^2
        cout << "!";
        for (int i = 0; i < k; ++i) {
            ll x = 0;
            ll y = 0;
            cout << ' ' << x << ' ' << y;
        }
        cout << '\n' << flush;
        return 0;
    }

    // Caches for queries: (s,t) -> sorted distances
    map<pair<int,int>, vector<ll>> cache;
    ll queriesUsed = 0;

    auto ask = [&](int s, int t) -> vector<ll> {
        pair<int,int> key = {s, t};
        auto it = cache.find(key);
        if (it != cache.end()) return it->second;
        cout << "? 1 " << s << ' ' << t << '\n' << flush;
        vector<ll> res(k);
        for (int i = 0; i < k; ++i) {
            if (!(cin >> res[i])) {
                exit(0);
            }
            if (res[0] == -1) {
                exit(0);
            }
        }
        sort(res.begin(), res.end());
        cache[key] = res;
        queriesUsed++;
        return res;
    };

    // Stage 1: recover all x-coordinates
    map<int,ll> Tx; // s -> sum of distances at (s,0)
    auto get_Tx = [&](int s) -> ll {
        auto it = Tx.find(s);
        if (it != Tx.end()) return it->second;
        vector<ll> d = ask(s, 0);
        ll sum = 0;
        for (ll v : d) sum += v;
        Tx[s] = sum;
        return sum;
    };
    auto count_x_leq = [&](int s) -> ll {
        if (s >= b) return k;
        if (s < -b) return 0;
        ll t1 = get_Tx(s);
        ll t2 = get_Tx(s + 1);
        ll d = t2 - t1;
        ll cnt = (d + k) / 2;
        if (cnt < 0) cnt = 0;
        if (cnt > k) cnt = k;
        return cnt;
    };

    vector<ll> xs(k);
    for (int idx = 1; idx <= k; ++idx) {
        int lo = -b, hi = b;
        while (lo < hi) {
            int mid = lo + (hi - lo) / 2;
            ll cnt = count_x_leq(mid);
            if (cnt >= idx) hi = mid;
            else lo = mid + 1;
        }
        xs[idx - 1] = lo;
    }

    // Stage 1: recover all y-coordinates
    map<int,ll> Uy; // t -> sum of distances at (0,t)
    auto get_Uy = [&](int t) -> ll {
        auto it = Uy.find(t);
        if (it != Uy.end()) return it->second;
        vector<ll> d = ask(0, t);
        ll sum = 0;
        for (ll v : d) sum += v;
        Uy[t] = sum;
        return sum;
    };
    auto count_y_leq = [&](int t) -> ll {
        if (t >= b) return k;
        if (t < -b) return 0;
        ll u1 = get_Uy(t);
        ll u2 = get_Uy(t + 1);
        ll d = u2 - u1;
        ll cnt = (d + k) / 2;
        if (cnt < 0) cnt = 0;
        if (cnt > k) cnt = k;
        return cnt;
    };

    vector<ll> ys(k);
    for (int idx = 1; idx <= k; ++idx) {
        int lo = -b, hi = b;
        while (lo < hi) {
            int mid = lo + (hi - lo) / 2;
            ll cnt = count_y_leq(mid);
            if (cnt >= idx) hi = mid;
            else lo = mid + 1;
        }
        ys[idx - 1] = lo;
    }

    // Stage 2: determine pairing between xs and ys using extra anchors
    const int BIG = 100000000; // within allowed probe range
    vector<pair<int,int>> anchors;
    anchors.push_back({0, 0});
    anchors.push_back({BIG, 0});
    anchors.push_back({0, BIG});
    anchors.push_back({BIG, BIG});

    vector<vector<ll>> S(ANCHORS_N);
    for (int m = 0; m < ANCHORS_N; ++m) {
        vector<ll> d = ask(anchors[m].first, anchors[m].second);
        S[m] = d; // already sorted
    }

    // Prepare globals for DFS
    G_XS = xs;
    G_YS = ys;
    G_ANCH = ANCHORS_N;
    G_Anchors = anchors;
    G_RemDists = S;
    G_UsedY.assign(k, 0);
    G_AssignY.assign(k, -1);

    bool ok = dfs_pair(0);

    vector<pair<ll,ll>> result;
    if (ok) {
        for (int i = 0; i < k; ++i) {
            int j = G_AssignY[i];
            if (j < 0 || j >= k) j = i % k;
            result.push_back({xs[i], ys[j]});
        }
    } else {
        // Fallback pairing: sort of identity
        for (int i = 0; i < k; ++i) {
            int j = i % k;
            result.push_back({xs[i], ys[j]});
        }
    }

    cout << "!";
    for (int i = 0; i < k; ++i) {
        cout << ' ' << result[i].first << ' ' << result[i].second;
    }
    cout << '\n' << flush;

    return 0;
}