#include <bits/stdc++.h>
using namespace std;

using ll = long long;

struct PairInfo {
    int a, b;
    ll base, dist, improve;
};

ll n_global;

// compute cycle distance between a and b (1..n)
inline ll cycDist(int a, int b, ll n) {
    ll d = llabs((ll)a - (ll)b);
    return min(d, n - d);
}

inline int prevv(int x, ll n) {
    if (x == 1) return (int)n;
    return x - 1;
}
inline int nextt(int x, ll n) {
    if (x == n) return 1;
    return x + 1;
}

// move from x by k steps along direction dir (+1 for next, -1 for prev)
int moveSteps(int x, ll k, int dir, ll n) {
    ll pos = (ll)x - 1;
    if (dir == 1) {
        pos = (pos + (k % n)) % n;
    } else {
        ll t = (k % n);
        pos = (pos - t) % n;
        if (pos < 0) pos += n;
    }
    return (int)(pos + 1);
}

ll query_count = 0;

ll query(int x, int y) {
    cout << "? " << x << " " << y << endl;
    cout.flush();
    ll res;
    if (!(cin >> res)) exit(0);
    ++query_count;
    return res;
}

bool guessAns(int u, int v) {
    cout << "! " << u << " " << v << endl;
    cout.flush();
    int r;
    if (!(cin >> r)) exit(0);
    return r == 1;
}

// Find endpoint reached from 'start' towards 'other' along direction 'dir' on the shortest path of length D.
// Assumes that moving along dir from 'start' is along some shortest path to 'other' (i.e., neighbor in that dir reduces distance by 1).
int find_endpoint_dir(int start, int other, ll D, int dir, ll n) {
    ll lo = 0, hi = D; // max steps along cycle from start before taking chord
    while (lo < hi) {
        ll mid = (lo + hi + 1) >> 1;
        int midv = moveSteps(start, mid, dir, n);
        ll dmid = query(midv, other);
        if (dmid + mid == D) {
            lo = mid;
        } else {
            hi = mid - 1;
        }
    }
    int endpoint = moveSteps(start, lo, dir, n);
    return endpoint;
}

// Try to compute endpoints from a pair (a,b) whose distance uses the chord (i.e., d < base).
// Returns pair<u,v> with d(u,v)=1.
pair<int,int> compute_from_pair(int a, int b, ll Dab, ll base, ll n) {
    // if Dab == 1 and (a,b) are not adjacent along cycle -> directly the chord
    if (Dab == 1 && cycDist(a,b,n) > 1) {
        return {a,b};
    }
    // Determine directions
    bool dirApos = false, dirAneg = false, dirBpos = false, dirBneg = false;

    ll dAprev = query(prevv(a,n), b);
    ll dAnext = query(nextt(a,n), b);
    if (dAprev == Dab - 1) dirAneg = true;
    if (dAnext == Dab - 1) dirApos = true;

    ll dBprev = query(prevv(b,n), a);
    ll dBnext = query(nextt(b,n), a);
    if (dBprev == Dab - 1) dirBneg = true;
    if (dBnext == Dab - 1) dirBpos = true;

    // If neither neighbor of a works, then 'a' must be an endpoint and the path starts with chord.
    // Similarly for b.
    // Attempt strategies trying possible directions (up to 4 combinations).
    vector<pair<int,int>> candidates;

    vector<int> dirsA, dirsB;
    if (dirAneg) dirsA.push_back(-1);
    if (dirApos) dirsA.push_back(+1);
    if (!dirAneg && !dirApos) dirsA.push_back(0); // means a itself is endpoint

    if (dirBneg) dirsB.push_back(-1);
    if (dirBpos) dirsB.push_back(+1);
    if (!dirBneg && !dirBpos) dirsB.push_back(0); // b is endpoint

    // try all combinations
    for (int da : dirsA) {
        int u = -1;
        ll A = 0;
        if (da == 0) {
            // a is an endpoint
            u = a;
            // Path length Dab = 1 + distance along cycle from b to other endpoint
            // We'll compute v via side of b
        } else {
            u = find_endpoint_dir(a, b, Dab, da, n);
            A = 0; // not needed explicitly
        }

        for (int db : dirsB) {
            int v = -1;
            if (db == 0) {
                v = b;
            } else {
                v = find_endpoint_dir(b, a, Dab, db, n);
            }
            // Validate candidate (u,v)
            if (u != -1 && v != -1) {
                if (cycDist(u, v, n) > 1) {
                    ll d_uv = query(u, v);
                    if (d_uv == 1) {
                        return {u, v};
                    }
                }
            }
            // If one side is endpoint, we can try to deduce other via check: the chord must connect to the other endpoint.
            // But above validation will handle correctness anyway.
        }
    }

    // If not found, as a fallback, try combinations where we swap roles (use alternative directions even if not reducing by 1),
    // though generally unnecessary. We'll try both directions from a and b if not tried.
    vector<int> alldirs = {-1, +1};
    for (int da : alldirs) {
        int u = find_endpoint_dir(a, b, Dab, da, n);
        for (int db : alldirs) {
            int v = find_endpoint_dir(b, a, Dab, db, n);
            if (cycDist(u, v, n) > 1) {
                ll d_uv = query(u, v);
                if (d_uv == 1) return {u, v};
            }
        }
    }

    // As last resort, return {-1,-1}
    return {-1,-1};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        ll n;
        cin >> n;
        n_global = n;
        query_count = 0;

        auto deltaC = [&](int x, int y){ return cycDist(x,y,n); };

        // For small n, brute force all pairs
        if (n <= 32) {
            bool done = false;
            for (int i = 1; i <= (int)n && !done; ++i) {
                for (int j = i+1; j <= (int)n && !done; ++j) {
                    if (deltaC(i,j) == 1) continue;
                    ll d = query(i,j);
                    if (d == 1) {
                        bool ok = guessAns(i,j);
                        if (!ok) return 0;
                        done = true;
                    }
                }
            }
            if (!done) {
                // Should not happen; as fallback, guess adjacent (invalid), but we must output something:
                // We'll guess 1 3 for n>=4 (non-adjacent)
                int u = 1, v = 3;
                if (n == 4) v = 3;
                bool ok = guessAns(u, v);
                if (!ok) return 0;
            }
            continue;
        }

        // Stage 1: choose anchors and query pairwise distances to find a pair whose distance is improved.
        auto process_with_m = [&](int m, pair<int,int>& found_uv)->bool {
            vector<int> A;
            A.reserve(m);
            for (int i = 0; i < m; ++i) {
                ll pos = ( ( (__int128)i * (__int128)n ) / m );
                int v = (int)(pos % n) + 1;
                A.push_back(v);
            }
            // Make unique if duplicates (in rare cases n < m)
            sort(A.begin(), A.end());
            A.erase(unique(A.begin(), A.end()), A.end());
            int M = (int)A.size();
            vector<PairInfo> cand;
            cand.reserve((size_t)M * (M-1) / 2);

            for (int i = 0; i < M; ++i) {
                for (int j = i+1; j < M; ++j) {
                    ll base = deltaC(A[i], A[j]);
                    ll d = query(A[i], A[j]);
                    ll improve = base - d;
                    if (improve > 0) {
                        cand.push_back({A[i], A[j], base, d, improve});
                    }
                }
            }
            if (cand.empty()) return false;
            sort(cand.begin(), cand.end(), [&](const PairInfo& p, const PairInfo& q){
                if (p.improve != q.improve) return p.improve > q.improve;
                if (p.dist != q.dist) return p.dist < q.dist;
                if (p.base != q.base) return p.base > q.base;
                if (p.a != q.a) return p.a < q.a;
                return p.b < q.b;
            });

            // Try top K candidate pairs to compute endpoints.
            int K = min((int)cand.size(), 6);
            for (int k = 0; k < K; ++k) {
                auto &pi = cand[k];
                auto pr = compute_from_pair(pi.a, pi.b, pi.dist, pi.base, n);
                if (pr.first != -1) {
                    found_uv = pr;
                    return true;
                }
                // Also try swapped order, might help (though symmetric)
                pr = compute_from_pair(pi.b, pi.a, pi.dist, pi.base, n);
                if (pr.first != -1) {
                    found_uv = pr;
                    return true;
                }
            }
            return false;
        };

        pair<int,int> uv = {-1,-1};
        bool okFound = false;
        // First try m=20
        okFound = process_with_m((int)min<ll>(20, n), uv);
        if (!okFound) {
            // escalate to m=30 if possible
            int m2 = (int)min<ll>(30, n);
            okFound = process_with_m(m2, uv);
        }
        if (!okFound || uv.first == -1) {
            // As a fallback, try random sampling of pairs to locate improved pair and then binary search.
            // We'll sample S=50 random pairs.
            vector<int> nodes;
            int S = (int)min<ll>(120, n);
            nodes.reserve(S);
            // choose evenly spaced plus random offset
            ll step = n / S;
            if (step == 0) step = 1;
            for (ll i = 0, cnt = 0; cnt < S && i < n; i += step, ++cnt) {
                nodes.push_back((int)((i % n) + 1));
            }
            vector<PairInfo> cand;
            for (int i = 0; i < (int)nodes.size(); ++i) {
                for (int j = i+1; j < (int)nodes.size(); ++j) {
                    ll base = cycDist(nodes[i], nodes[j], n);
                    ll d = query(nodes[i], nodes[j]);
                    if (base - d > 0) {
                        cand.push_back({nodes[i], nodes[j], base, d, base - d});
                    }
                }
            }
            sort(cand.begin(), cand.end(), [&](const PairInfo& p, const PairInfo& q){
                if (p.improve != q.improve) return p.improve > q.improve;
                if (p.dist != q.dist) return p.dist < q.dist;
                if (p.base != q.base) return p.base > q.base;
                if (p.a != q.a) return p.a < q.a;
                return p.b < q.b;
            });
            for (int k = 0; k < (int)min<size_t>(cand.size(), 8); ++k) {
                auto &pi = cand[k];
                auto pr = compute_from_pair(pi.a, pi.b, pi.dist, pi.base, n);
                if (pr.first != -1) {
                    uv = pr;
                    okFound = true;
                    break;
                }
                pr = compute_from_pair(pi.b, pi.a, pi.dist, pi.base, n);
                if (pr.first != -1) {
                    uv = pr;
                    okFound = true;
                    break;
                }
            }
            if (!okFound) {
                // As a last ditch, attempt to find any pair (x,y) with distance 1 and non-adjacent by sampling random pairs up to remaining budget
                int tries = 200;
                std::mt19937_64 rng(712367 + (unsigned)chrono::high_resolution_clock::now().time_since_epoch().count());
                while (tries-- > 0 && query_count < 495 && !okFound) {
                    int x = (int)(rng() % n) + 1;
                    int y = (int)(rng() % n) + 1;
                    if (x == y) continue;
                    if (deltaC(x,y) == 1) continue;
                    ll d = query(x,y);
                    if (d == 1) {
                        uv = {x,y};
                        okFound = true;
                        break;
                    }
                }
            }
        }

        if (!okFound || uv.first == -1) {
            // Fallback guess something (shouldn't happen)
            int u = 1, v = 3;
            if (cycDist(u, v, n) == 1) v = 4;
            bool ok = guessAns(u, v);
            if (!ok) return 0;
        } else {
            bool ok = guessAns(uv.first, uv.second);
            if (!ok) return 0;
        }
    }
    return 0;
}