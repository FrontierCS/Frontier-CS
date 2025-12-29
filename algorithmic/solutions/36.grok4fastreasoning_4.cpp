#include <bits/stdc++.h>
using namespace std;
using ll = long long;

mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());

const ll MOD = 1000000000000000000LL;
const int K = 20000;
const int NUM_MULT = 3;

ll query(const vector<ll>& seq) {
    if (seq.empty()) return 0;
    cout << 0 << " " << seq.size() << " ";
    for (auto v : seq) cout << v << " ";
    cout << endl;
    cout.flush();
    ll res;
    cin >> res;
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    cout.tie(nullptr);

    vector<ll> multiples;
    while (multiples.size() < NUM_MULT) {
        vector<ll> x(K + 1);
        for (int i = 1; i <= K; ++i) {
            x[i] = (rng() % MOD) + 1;
        }
        vector<ll> allx(K);
        for (int i = 0; i < K; ++i) allx[i] = x[i + 1];
        ll cc = query(allx);
        if (cc == 0) continue;

        // Find j: binary search for smallest p with prefix C > 0
        int lo = 1, hi = K;
        while (lo < hi) {
            int mi = (lo + hi) / 2;
            vector<ll> pref(mi);
            for (int t = 0; t < mi; ++t) pref[t] = x[t + 1];
            ll ccp = query(pref);
            if (ccp > 0) {
                hi = mi;
            } else {
                lo = mi + 1;
            }
        }
        int jj = lo;
        // Verify
        vector<ll> prefv(jj);
        for (int t = 0; t < jj; ++t) prefv[t] = x[t + 1];
        ll cjv = query(prefv);
        if (cjv == 0) continue; // rare error, retry

        // Now find i < jj with x[i] == x[jj] mod n
        lo = 1, hi = jj - 1;
        while (lo < hi) {
            int mi = (lo + hi) / 2;
            vector<ll> S(mi - lo + 1);
            for (int t = lo; t <= mi; ++t) S[t - lo] = x[t];
            ll cs = query(S);
            vector<ll> St = S;
            St.push_back(x[jj]);
            ll ct = query(St);
            ll matches = ct - cs;
            if (matches > 0) {
                hi = mi;
            } else {
                lo = mi + 1;
            }
        }
        int ii = lo;

        // Verify pair
        vector<ll> pr = {x[ii], x[jj]};
        ll cp = query(pr);
        if (cp != 1) continue; // error, retry

        ll mm = abs(x[ii] - x[jj]);
        multiples.push_back(mm);
    }

    ll nn = multiples[0];
    for (size_t i = 1; i < multiples.size(); ++i) {
        nn = __gcd(nn, multiples[i]);
    }

    // Verification
    int vsize = 1000;
    vector<ll> verif(vsize);
    for (int i = 0; i < vsize; ++i) {
        verif[i] = (rng() % MOD) + 1;
    }
    ll c_ver = query(verif);

    // Compute expected
    vector<ll> resids(vsize);
    for (int i = 0; i < vsize; ++i) {
        resids[i] = verif[i] % nn;
        if (resids[i] < 0) resids[i] += nn; // in case
    }
    sort(resids.begin(), resids.end());
    ll exp_c = 0;
    int cur = 1;
    for (int i = 1; i < vsize; ++i) {
        if (resids[i] == resids[i - 1]) {
            ++cur;
        } else {
            exp_c += (ll)cur * (cur - 1) / 2;
            cur = 1;
        }
    }
    exp_c += (ll)cur * (cur - 1) / 2;

    // Assume matches, output
    cout << 1 << " " << nn << endl;
    cout.flush();
    return 0;
}