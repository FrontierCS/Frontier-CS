#include <bits/stdc++.h>
using namespace std;

static constexpr int MAXN = 205;

struct Oracle {
    int n;
    unordered_map<string, int> cache;
    int queryCount = 0;

    explicit Oracle(int n_ = 0) : n(n_) {
        cache.reserve(8192);
        cache.max_load_factor(0.7f);
    }

    int getF(const bitset<MAXN>& mask) {
        int cnt = (int)mask.count();
        if (cnt == 0 || cnt == n) return 0;

        string s;
        s.resize(n);
        for (int i = 0; i < n; i++) s[i] = mask.test(i) ? '1' : '0';

        auto it = cache.find(s);
        if (it != cache.end()) return it->second;

        cout << "? " << s << '\n' << flush;

        int ans;
        if (!(cin >> ans)) exit(0);
        if (ans == -1) exit(0);

        cache.emplace(std::move(s), ans);
        queryCount++;
        return ans;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;

    while (T--) {
        int n;
        cin >> n;

        Oracle oracle(n);

        if (n <= 1) {
            cout << "! 1\n" << flush;
            continue;
        }

        bitset<MAXN> R;
        R.reset();
        R.set(0);

        int FR = oracle.getF(R);

        while ((int)R.count() < n && FR > 0) {
            vector<int> cand;
            cand.reserve(n);
            for (int i = 0; i < n; i++) if (!R.test(i)) cand.push_back(i);

            while (cand.size() > 1) {
                int mid = (int)cand.size() / 2;
                bitset<MAXN> B;
                B.reset();
                for (int i = 0; i < mid; i++) B.set(cand[i]);

                bitset<MAXN> U = R | B;

                int FB = oracle.getF(B);
                int FU = oracle.getF(U);

                long long H = (long long)FR + FB - FU;
                if (H > 0) {
                    cand.resize(mid);
                } else {
                    vector<int> right;
                    right.reserve((int)cand.size() - mid);
                    for (int i = mid; i < (int)cand.size(); i++) right.push_back(cand[i]);
                    cand.swap(right);
                }
            }

            int v = cand[0];
            R.set(v);
            FR = oracle.getF(R);
        }

        int ans = ((int)R.count() == n) ? 1 : 0;
        cout << "! " << ans << '\n' << flush;
    }

    return 0;
}