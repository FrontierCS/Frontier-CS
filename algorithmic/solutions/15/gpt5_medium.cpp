#include <bits/stdc++.h>
using namespace std;

vector<int> apply_op(const vector<int>& p, int x, int y) {
    int n = (int)p.size();
    vector<int> q;
    q.reserve(n);
    // C
    q.insert(q.end(), p.begin() + (n - y), p.end());
    // B
    q.insert(q.end(), p.begin() + x, p.begin() + (n - y));
    // A
    q.insert(q.end(), p.begin(), p.begin() + x);
    return q;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<int> p(n);
    for (int i = 0; i < n; ++i) cin >> p[i];

    vector<pair<int,int>> ops;

    auto lexLess = [](const vector<int>& a, const vector<int>& b){
        return lexicographical_compare(a.begin(), a.end(), b.begin(), b.end());
    };

    if (n == 3) {
        vector<int> q = apply_op(p, 1, 1);
        if (lexLess(q, p)) {
            ops.emplace_back(1, 1);
            p = move(q);
        }
    } else {
        int pos1 = -1;
        for (int i = 0; i < n; ++i) if (p[i] == 1) { pos1 = i; break; }

        if (pos1 == 0) {
            // Do nothing; already minimal first element
        } else if (pos1 >= 2) {
            int y = n - pos1;
            int bestX = 1;
            vector<int> bestQ = apply_op(p, bestX, y);
            for (int x = 2; x <= pos1 - 0 - 1; ++x) {
                vector<int> q = apply_op(p, x, y);
                if (lexLess(q, bestQ)) {
                    bestQ = move(q);
                    bestX = x;
                }
            }
            ops.emplace_back(bestX, y);
            p = move(bestQ);
        } else { // pos1 == 1 (0-based)
            // Try two-step approach, but only take it if it improves lex order.
            // First op: x=1, y=2
            vector<int> p1 = apply_op(p, 1, 2);
            int pos1new = -1;
            for (int i = 0; i < n; ++i) if (p1[i] == 1) { pos1new = i; break; }
            int y2 = n - pos1new;

            int bestX2 = 1;
            vector<int> bestQ2 = apply_op(p1, bestX2, y2);
            for (int x2 = 2; x2 <= pos1new - 0 - 1; ++x2) {
                vector<int> q2 = apply_op(p1, x2, y2);
                if (lexLess(q2, bestQ2)) {
                    bestQ2 = move(q2);
                    bestX2 = x2;
                }
            }
            if (lexLess(bestQ2, p)) {
                ops.emplace_back(1, 2);
                ops.emplace_back(bestX2, y2);
                p = move(bestQ2);
            }
        }
    }

    cout << ops.size() << "\n";
    for (auto &op : ops) {
        cout << op.first << " " << op.second << "\n";
    }
    return 0;
}