#include <bits/stdc++.h>
using namespace std;

struct Point {
    int x, y;
};

int dist(Point a, Point b) {
    return abs(a.x - b.x) + abs(a.y - b.y);
}

int main() {
    vector<Point> A(1001), B(1001);
    for (int i = 1; i <= 1000; i++) {
        cin >> A[i].x >> A[i].y >> B[i].x >> B[i].y;
    }
    Point O = {400, 400};
    vector<pair<int, int>> cand;
    for (int i = 1; i <= 1000; i++) {
        int c = dist(O, A[i]) + dist(A[i], B[i]) + dist(B[i], O);
        cand.emplace_back(c, i);
    }
    sort(cand.begin(), cand.end());
    vector<int> S;
    for (int i = 0; i < 50; i++) {
        S.push_back(cand[i].second);
    }
    int N = 50;
    vector<Point> tasks(2 * N);
    for (int i = 0; i < N; i++) {
        int idx = S[i];
        tasks[i] = A[idx];
        tasks[i + N] = B[idx];
    }
    set<int> ready;
    for (int i = 0; i < N; i++) ready.insert(i);
    vector<bool> vis(2 * N, false);
    vector<int> order;
    Point curr = O;
    for (int step = 0; step < 2 * N; step++) {
        int best = -1;
        int md = INT_MAX;
        for (int j : ready) {
            if (vis[j]) continue;
            int d = dist(curr, tasks[j]);
            if (d < md || (d == md && j < best)) {
                md = d;
                best = j;
            }
        }
        assert(best != -1);
        order.push_back(best);
        vis[best] = true;
        curr = tasks[best];
        ready.erase(best);
        if (best < N) {
            int deliv = best + N;
            if (!vis[deliv]) ready.insert(deliv);
        }
    }
    vector<Point> path;
    path.push_back(O);
    for (int j : order) {
        path.push_back(tasks[j]);
    }
    path.push_back(O);
    cout << 50;
    for (int idx : S) cout << " " << idx;
    cout << endl;
    cout << path.size();
    for (auto p : path) {
        cout << " " << p.x << " " << p.y;
    }
    cout << endl;
    return 0;
}