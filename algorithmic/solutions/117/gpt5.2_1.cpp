#include <bits/stdc++.h>
using namespace std;

using ll = long long;
using ld = long double;

static constexpr int QMAX = 10000;

struct SplitMix64Hash {
    size_t operator()(ll x) const noexcept {
        static const uint64_t FIXED_RANDOM = chrono::steady_clock::now().time_since_epoch().count();
        uint64_t z = (uint64_t)x + FIXED_RANDOM + 0x9e3779b97f4a7c15ULL;
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return (size_t)(z ^ (z >> 31));
    }
};

struct Interactor {
    ll X;
    int qcnt = 0;

    unordered_map<ll, ld, SplitMix64Hash> fcache; // key: y2 = 2*y

    explicit Interactor(ll X_) : X(X_) {
        fcache.reserve(1 << 15);
        fcache.max_load_factor(0.7f);
    }

    ld askF_y2(ll y2) {
        auto it = fcache.find(y2);
        if (it != fcache.end()) return it->second;

        if (qcnt >= QMAX) {
            exit(0);
        }
        ++qcnt;

        ld y = (ld)y2 / 2.0L;
        cout << "? " << X << " " << y << "\n" << flush;

        ld ans;
        if (!(cin >> ans)) exit(0);
        if (ans < -0.5) exit(0); // interactor error signal (if any)

        fcache.emplace(y2, ans);
        return ans;
    }
};

static inline ll round_nearest_div(ll y, ll X) {
    // X > 0, and we assume |remainder| < X/2 so nearest integer is well-defined.
    ll half = X / 2;
    if (y >= 0) return (y + half) / X;
    return -(((-y) + half) / X);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    cout.setf(std::ios::fixed);
    cout << setprecision(20);

    const ll X = 20001; // > 2*10000, ensures a = round(y/X) from y = aX + b with |b|<=10000
    Interactor I(X);

    auto getD = [&](ll k) -> ld {
        // D(k) = F(k+0.5) - F(k-0.5) = sum +/- 1/sqrt(a^2+1)
        // Use y2 = 2y keys: (k+0.5)*2 = 2k+1, (k-0.5)*2 = 2k-1
        ld fp = I.askF_y2(2 * k + 1);
        ld fm = I.askF_y2(2 * k - 1);
        return fp - fm;
    };

    const ll minY = -10000LL * X - 10000LL;
    const ll maxY = +10000LL * X + 10000LL;
    const ll L = minY - 1;
    const ll R = maxY;

    const ld EPS = 5e-5L;

    struct Node {
        ll l, r;
        ld Dl, Dr;
    };

    vector<ll> cand;
    cand.reserve(n * 4);

    ld DL = getD(L);
    ld DR = getD(R);

    vector<Node> st;
    st.reserve(8192);
    st.push_back({L, R, DL, DR});

    while (!st.empty()) {
        Node cur = st.back();
        st.pop_back();

        if (fabsl(cur.Dl - cur.Dr) <= EPS) continue;

        if (cur.l + 1 == cur.r) {
            cand.push_back(cur.r);
            continue;
        }

        ll m = (cur.l + cur.r) / 2;
        ld Dm = getD(m);
        st.push_back({m, cur.r, Dm, cur.Dr});
        st.push_back({cur.l, m, cur.Dl, Dm});
    }

    sort(cand.begin(), cand.end());
    cand.erase(unique(cand.begin(), cand.end()), cand.end());

    vector<pair<ld, ll>> jumps;
    jumps.reserve(cand.size());

    for (ll y : cand) {
        ld j = fabsl(getD(y) - getD(y - 1));
        jumps.push_back({j, y});
    }

    sort(jumps.begin(), jumps.end(), [&](const auto& a, const auto& b) {
        if (a.first != b.first) return a.first > b.first;
        return a.second < b.second;
    });

    vector<ll> ys;
    ys.reserve(n);
    for (int i = 0; i < (int)jumps.size() && (int)ys.size() < n; i++) {
        ys.push_back(jumps[i].second);
    }
    sort(ys.begin(), ys.end());

    if ((int)ys.size() != n) {
        // Fallback: output something (should not happen with a correct interactor)
        cout << "!";
        for (int i = 0; i < n; i++) cout << " 0";
        for (int i = 0; i < n; i++) cout << " 0";
        cout << "\n" << flush;
        return 0;
    }

    vector<ll> a(n), b(n);
    for (int i = 0; i < n; i++) {
        ll y = ys[i];
        ll ai = round_nearest_div(y, X);
        ll bi = y - ai * X;
        a[i] = ai;
        b[i] = bi;
    }

    cout << "!";
    for (int i = 0; i < n; i++) cout << " " << a[i];
    for (int i = 0; i < n; i++) cout << " " << b[i];
    cout << "\n" << flush;

    return 0;
}