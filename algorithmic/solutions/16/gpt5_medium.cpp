#include <bits/stdc++.h>
using namespace std;

using ll = long long;

static inline ll norm_idx(ll x, ll n){
    // keep 1..n
    ll r = (x % n + n) % n;
    if(r == 0) r = n;
    return r;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if(!(cin >> T)) return 0;
    while(T--){
        ll n;
        cin >> n;

        auto ask = [&](ll x, ll y)->ll{
            cout << "? " << x << " " << y << endl;
            cout.flush();
            ll d;
            if(!(cin >> d)) exit(0);
            return d;
        };

        auto finish = [&](ll u, ll v){
            cout << "! " << u << " " << v << endl;
            cout.flush();
            int r;
            if(!(cin >> r)) exit(0);
            if(r == -1) exit(0);
        };

        // Helper to find minimal t in [1..m] such that dist(c, c + s * t) < t
        auto find_first_less = [&](ll c, int s)->pair<ll,ll>{
            ll m = n/2;
            ll lo = 1, hi = m;
            while(lo < hi){
                ll mid = (lo + hi) / 2;
                ll w = norm_idx(c + s*mid, n);
                ll dcm = ask(c, w);
                if(dcm < mid) hi = mid;
                else lo = mid + 1;
            }
            ll t0 = lo;
            // derive s_dir from t0
            ll cand = 2*t0 - 2;
            if(cand < 2) cand = 2; // minimal non-adjacent
            ll wtest = norm_idx(c + s*cand, n);
            ll dtest = ask(c, wtest);
            ll s_dir = (dtest == 1 ? cand : cand - 1);
            return {t0, s_dir};
        };

        auto find_partner = [&](ll c)->ll{
            ll m = n/2;
            // Two directions
            auto p1 = find_first_less(c, +1);
            auto p2 = find_first_less(c, -1);
            ll s_plus = p1.second;
            ll s_minus = p2.second;
            ll dir_sign = +1;
            ll L = s_plus;
            if(s_minus < s_plus){
                dir_sign = -1;
                L = s_minus;
            }
            ll cand = norm_idx(c + dir_sign*L, n);
            ll d1 = ask(c, cand);
            if(d1 == 1) return cand;
            else{
                // must be the other side (equal L case)
                ll cand2 = norm_idx(c - dir_sign*L, n);
                return cand2;
            }
        };

        // Try multiple roots to find an x where chord helps
        vector<ll> roots;
        roots.push_back(1);
        if(n >= 3){
            roots.push_back(norm_idx(1 + n/3, n));
            roots.push_back(norm_idx(1 + (2*(n/3)), n));
        }

        bool solved = false;

        for(size_t rid = 0; rid < roots.size() && !solved; ++rid){
            ll r = roots[rid];
            ll m = n/2;

            // Sampling to find x with d(r,x) < min(|x - r|, n - |x - r|)
            ll P_each = 40;
            vector<ll> ts;
            if(m <= 80){
                for(ll t = 2; t <= m; ++t) ts.push_back(t);
            }else{
                set<ll> uniq;
                for(ll i = 0; i < P_each; ++i){
                    long double pos = ( (long double)(i) + 0.5L ) * (long double)m / (long double)P_each;
                    ll t = (ll)floor(pos + 1e-12L);
                    t = max<ll>(2, min<ll>(t, m));
                    uniq.insert(t);
                }
                for(auto t: uniq) ts.push_back(t);
            }

            bool found = false;
            ll x = -1;
            ll dx = -1;

            // Check both directions with balanced sampling
            for(ll t: ts){
                ll xp = norm_idx(r + t, n);
                ll d1 = ask(r, xp);
                if(d1 < t){
                    x = xp; dx = d1; found = true; break;
                }
                ll xm = norm_idx(r - t, n);
                ll d2 = ask(r, xm);
                if(d2 < t){
                    x = xm; dx = d2; found = true; break;
                }
            }
            if(!found) continue;

            // Determine if r is an endpoint
            ll r_plus = norm_idx(r + 1, n);
            ll r_minus = norm_idx(r - 1, n);
            int dir = 0; // +1 for +, -1 for -
            ll dplus = ask(r_plus, x);
            if(dplus == dx - 1) dir = +1;
            else{
                ll dminus = ask(r_minus, x);
                if(dminus == dx - 1) dir = -1;
                else{
                    // r is endpoint
                    ll c = r;
                    ll d = find_partner(c);
                    finish(c, d);
                    solved = true;
                    break;
                }
            }

            // Binary search for last t where "first step towards x from w is dir"
            auto first_step_ok = [&](ll w, int dir)->bool{
                ll wnext = norm_idx(w + dir, n);
                ll dwx = ask(w, x);
                ll dnx = ask(wnext, x);
                return (dnx == dwx - 1);
            };

            ll lo = 0, hi = m;
            while(lo < hi){
                ll mid = (lo + hi + 1) / 2;
                ll w = norm_idx(r + dir * mid, n);
                if(first_step_ok(w, dir)) lo = mid;
                else hi = mid - 1;
            }
            ll c = norm_idx(r + dir * lo, n);

            ll d = find_partner(c);
            finish(c, d);
            solved = true;
            break;
        }

        if(!solved){
            // Fallback: very unlikely. Try assume root 1 is endpoint via partner search.
            ll c = 1;
            ll d = -1;
            // Use partner finder from c=1
            auto partner = [&](ll c)->ll{
                return find_partner(c);
            };
            d = partner(c);
            finish(c, d);
        }
    }

    return 0;
}