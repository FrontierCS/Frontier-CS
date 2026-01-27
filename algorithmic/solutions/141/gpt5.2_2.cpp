#include <bits/stdc++.h>
using namespace std;

static int n, k;
static int ops = 0;

static char queryBakery(int c) {
    cout << "? " << c << '\n';
    cout.flush();
    string s;
    if (!(cin >> s)) exit(0);
    ++ops;
    return s[0];
}

static void resetMemory() {
    cout << "R\n";
    cout.flush();
    ++ops;
}

static vector<int> mergeSetsKge2(const vector<int>& A0, const vector<int>& B0) {
    const vector<int> *Ap = &A0, *Bp = &B0;
    if (Ap->size() < Bp->size()) swap(Ap, Bp);
    const vector<int>& A = *Ap;
    const vector<int>& B = *Bp;

    int a = (int)A.size();
    int b = (int)B.size();
    vector<char> matched(b, 0);

    int m = max(1, k / 2);
    int t = k - m;
    if (t <= 0) t = 1;

    vector<int> rem;
    rem.reserve(b);
    for (int i = 0; i < b; i++) rem.push_back(i);

    for (int startA = 0; startA < a && !rem.empty(); startA += m) {
        int endA = min(a, startA + m);

        for (int p = 0; p < (int)rem.size(); p += t) {
            int q = min((int)rem.size(), p + t);

            resetMemory();
            for (int i = startA; i < endA; i++) (void)queryBakery(A[i]);

            for (int j = p; j < q; j++) {
                int bi = rem[j];
                char ans = queryBakery(B[bi]);
                if (ans == 'Y') matched[bi] = 1;
            }
        }

        vector<int> newRem;
        newRem.reserve(rem.size());
        for (int bi : rem) if (!matched[bi]) newRem.push_back(bi);
        rem.swap(newRem);
    }

    vector<int> res;
    res.reserve(a + b);
    res.insert(res.end(), A.begin(), A.end());
    for (int i = 0; i < b; i++) if (!matched[i]) res.push_back(B[i]);
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n >> k;

    if (k == 1) {
        vector<int> reps;
        reps.reserve(n);

        for (int i = 1; i <= n; i++) {
            bool found = false;
            for (int rep : reps) {
                resetMemory();
                (void)queryBakery(rep);
                char ans = queryBakery(i);
                if (ans == 'Y') {
                    found = true;
                    break;
                }
            }
            if (!found) reps.push_back(i);
        }

        cout << "! " << (int)reps.size() << '\n';
        cout.flush();
        return 0;
    }

    vector<vector<int>> groups;
    groups.reserve(n / k);

    for (int start = 1; start <= n; start += k) {
        resetMemory();
        vector<int> reps;
        reps.reserve(k);
        for (int i = 0; i < k; i++) {
            int idx = start + i;
            char ans = queryBakery(idx);
            if (ans == 'N') reps.push_back(idx);
        }
        groups.push_back(std::move(reps));
    }

    while (groups.size() > 1) {
        vector<vector<int>> nxt;
        nxt.reserve(groups.size() / 2);
        for (size_t i = 0; i < groups.size(); i += 2) {
            nxt.push_back(mergeSetsKge2(groups[i], groups[i + 1]));
        }
        groups.swap(nxt);
    }

    int d = (int)groups[0].size();
    cout << "! " << d << '\n';
    cout.flush();
    return 0;
}