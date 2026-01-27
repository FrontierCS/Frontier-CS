#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<char> alive(n + 1, 0), good(n + 1, 0), inS(n + 1, 0);
    vector<int> A; A.reserve(n);
    for (int i = 1; i <= n; ++i) { alive[i] = 1; A.push_back(i); }

    auto ask = [&](const vector<int>& S) -> string {
        cout << "? " << S.size();
        for (int v : S) cout << " " << v;
        cout << endl;
        cout.flush();
        string ans;
        if (!(cin >> ans)) exit(0);
        return ans;
    };

    auto guess = [&](int g) {
        cout << "! " << g << endl;
        cout.flush();
        string resp;
        if (!(cin >> resp)) exit(0);
        if (!resp.empty() && resp[0] == ':' && resp.size() >= 2 && resp[1] == ')') exit(0);
    };

    auto update = [&](const vector<int>& S, const string& ans) {
        for (int v : S) inS[v] = 1;
        bool isYes = (!ans.empty() && (ans[0] == 'Y' || ans[0] == 'y'));
        vector<int> newA; newA.reserve(A.size());
        vector<char> newGood(n + 1, 0);
        for (int x : A) {
            bool truth = isYes ? (inS[x] == 1) : (inS[x] == 0);
            bool ng = truth;
            bool na = ng || (good[x] && !truth);
            if (na) {
                newA.push_back(x);
                if (ng) newGood[x] = 1;
            }
        }
        for (int v : S) inS[v] = 0;
        A.swap(newA);
        good.swap(newGood);
    };

    int queries = 0;
    auto querySet = [&](const vector<int>& S) {
        if (S.empty()) return;
        string ans = ask(S);
        ++queries;
        update(S, ans);
    };

    auto buildFirstK = [&](const vector<int>& pool, int k) {
        vector<int> res;
        res.reserve(k);
        for (int i = 0; i < (int)pool.size() && (int)res.size() < k; ++i) res.push_back(pool[i]);
        return res;
    };

    while ((int)A.size() > 2 && queries < 53) {
        vector<int> Qlist; Qlist.reserve(A.size());
        for (int x : A) if (!good[x]) Qlist.push_back(x);
        vector<int> S;
        int qsz = (int)Qlist.size();
        if (qsz == 0) {
            int cnt = (int)((A.size() + 1) / 2);
            S = buildFirstK(A, cnt);
        } else if (qsz == 1) {
            S = {Qlist[0]};
        } else {
            int y = qsz / 2;
            S = buildFirstK(Qlist, y);
        }
        querySet(S);
    }

    if (A.empty()) {
        guess(1);
        return 0;
    } else if ((int)A.size() == 1) {
        guess(A[0]);
        return 0;
    } else {
        guess(A[0]);
        if ((int)A.size() >= 2) guess(A[1]);
        return 0;
    }
}