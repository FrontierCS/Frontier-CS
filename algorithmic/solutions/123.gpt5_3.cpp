#include <bits/stdc++.h>
using namespace std;

static const string YES = "YES";
static const string NO = "NO";
static const string HAPPY = ":)";
static const string SAD = ":(";

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<char> inU(n + 1, 1), inA(n + 1, 1), inS(n + 1, 0);

    auto countSet = [&](const vector<char>& v)->int{
        int c = 0;
        for (int i = 1; i <= n; ++i) if (v[i]) ++c;
        return c;
    };

    auto getUList = [&]()->vector<int>{
        vector<int> res;
        for (int i = 1; i <= n; ++i) if (inU[i]) res.push_back(i);
        return res;
    };

    auto ask = [&](const vector<int>& S)->string{
        cout << "? " << S.size();
        for (int x : S) cout << " " << x;
        cout << endl;
        cout.flush();
        string ans;
        if (!(cin >> ans)) exit(0);
        return ans;
    };

    auto guess = [&](int g)->string{
        cout << "! " << g << endl;
        cout.flush();
        string ans;
        if (!(cin >> ans)) exit(0);
        return ans;
    };

    int questions_used = 0;

    while (true) {
        vector<int> Ulist = getUList();
        int u = (int)Ulist.size();
        if (u <= 2) break;
        if (questions_used >= 53) break;

        int a = countSet(inA);
        // choose s as close to u/2 as possible, but at least 1
        int s = u / 2;
        if (s == 0) s = 1;

        int tmin = max(0, s - (u - a));
        int tmax = min(a, s);
        // target t that balances E_yes and E_no
        double tstar_d = s + (a - u) / 2.0;
        int t = (int)llround(tstar_d);
        if (t < tmin) t = tmin;
        if (t > tmax) t = tmax;

        // Build S: pick t from A ∩ U and (s - t) from U \ A
        vector<int> S;
        S.reserve(s);
        int needA = t;
        int needNonA = s - t;

        for (int i = 1; i <= n && needA > 0; ++i) {
            if (inU[i] && inA[i]) {
                S.push_back(i);
                --needA;
            }
        }
        for (int i = 1; i <= n && needNonA > 0; ++i) {
            if (inU[i] && !inA[i]) {
                S.push_back(i);
                --needNonA;
            }
        }

        if (S.empty()) {
            // Asks must be non-empty; fallback: pick one from U
            for (int i = 1; i <= n; ++i) if (inU[i]) { S.push_back(i); break; }
        }

        string res = ask(S);
        ++questions_used;

        // prepare inS flags
        fill(inS.begin(), inS.end(), 0);
        for (int x : S) inS[x] = 1;

        vector<char> inANext(n + 1, 0), inUNext(n + 1, 0);

        if (res == YES) {
            for (int i = 1; i <= n; ++i) {
                bool a_i = inA[i];
                bool u_i = inU[i];
                bool s_i = inS[i];
                bool AN = (u_i && s_i);
                bool UN = (u_i && s_i) || (a_i && !s_i);
                inANext[i] = AN;
                inUNext[i] = UN;
            }
        } else { // treat anything else as NO
            for (int i = 1; i <= n; ++i) {
                bool a_i = inA[i];
                bool u_i = inU[i];
                bool s_i = inS[i];
                bool AN = (u_i && !s_i);
                bool UN = (u_i && !s_i) || (a_i && s_i);
                inANext[i] = AN;
                inUNext[i] = UN;
            }
        }

        inA.swap(inANext);
        inU.swap(inUNext);
    }

    vector<int> Ucand;
    for (int i = 1; i <= n; ++i) if (inU[i]) Ucand.push_back(i);

    if (Ucand.empty()) {
        // Fallback guess 1 then 2 or 1 if n==1
        int g = (n >= 1 ? 1 : 1);
        string ans = guess(g);
        if (ans == HAPPY) return 0;
        if (n >= 2) {
            ans = guess(2);
            if (ans == HAPPY) return 0;
        }
        return 0;
    }

    if (Ucand.size() == 1) {
        string ans = guess(Ucand[0]);
        if (ans == HAPPY) return 0;
        // If wrong, try fallback
        for (int i = 1; i <= n; ++i) if (i != Ucand[0]) {
            ans = guess(i);
            if (ans == HAPPY) return 0;
            break;
        }
        return 0;
    } else {
        // size >= 2
        string ans = guess(Ucand[0]);
        if (ans == HAPPY) return 0;
        ans = guess(Ucand[1]);
        if (ans == HAPPY) return 0;
        return 0;
    }
}