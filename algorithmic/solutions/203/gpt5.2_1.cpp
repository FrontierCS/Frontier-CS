#include <bits/stdc++.h>
using namespace std;

static int N;
static int qcnt = 0, acnt = 0;

int Query(const vector<int>& v) {
    cout << "Query " << (int)v.size();
    for (int x : v) cout << ' ' << x;
    cout << '\n';
    cout.flush();

    int res;
    if (!(cin >> res)) exit(0);
    if (res == -1) exit(0);
    ++qcnt;
    return res;
}

void Answer(int a, int b) {
    cout << "Answer " << a << ' ' << b << '\n';
    cout.flush();
    ++acnt;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> N)) return 0;
    const int M = 2 * N;

    vector<int> reps; // one representative per currently "open" color; all colors in reps are distinct
    reps.reserve(N);

    for (int x = 1; x <= M; x++) {
        if (reps.empty()) {
            reps.push_back(x);
            continue;
        }

        vector<int> all = reps;
        all.push_back(x);
        int r = Query(all);

        if (r == (int)reps.size() + 1) {
            reps.push_back(x);
            continue;
        }

        vector<int> cand = reps;
        while (cand.size() > 1) {
            int mid = (int)cand.size() / 2;
            vector<int> s;
            s.reserve(mid + 1);
            for (int i = 0; i < mid; i++) s.push_back(cand[i]);
            s.push_back(x);

            int rr = Query(s);
            if (rr == mid) {
                cand.resize(mid);
            } else {
                cand.erase(cand.begin(), cand.begin() + mid);
            }
        }

        int y = cand[0];
        Answer(x, y);

        auto it = find(reps.begin(), reps.end(), y);
        if (it != reps.end()) reps.erase(it);
    }

    return 0;
}