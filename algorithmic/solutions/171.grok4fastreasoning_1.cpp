#include <bits/stdc++.h>
using namespace std;

int main() {
  int N, M;
  cin >> N >> M;
  vector<pair<int, int>> points(M);
  for (int i = 0; i < M; i++) {
    cin >> points[i].first >> points[i].second;
  }
  vector<pair<char, char>> total;
  pair<int, int> current = points[0];
  int dx[4] = {-1, 1, 0, 0};
  int dy[4] = {0, 0, -1, 1};
  char dirch[4] = {'U', 'D', 'L', 'R'};
  for (int k = 1; k < M; k++) {
    int ti = points[k].first;
    int tj = points[k].second;
    if (current.first == ti && current.second == tj) continue;
    bool forbid[20][20];
    memset(forbid, 0, sizeof(forbid));
    for (int l = k + 1; l < M; l++) {
      int fi = points[l].first, fj = points[l].second;
      forbid[fi][fj] = true;
    }
    int NN = N * N;
    vector<int> dist(NN, -1);
    vector<int> prevv(NN, -1);
    vector<char> act(NN, 0);
    vector<char> direc(NN, 0);
    queue<int> q;
    int si = current.first, sj = current.second;
    int spos = si * N + sj;
    dist[spos] = 0;
    q.push(spos);
    while (!q.empty()) {
      int cur = q.front(); q.pop();
      int i = cur / N;
      int j = cur % N;
      for (int d = 0; d < 4; d++) {
        // move
        int ni = i + dx[d];
        int nj = j + dy[d];
        if (ni >= 0 && ni < N && nj >= 0 && nj < N) {
          int np = ni * N + nj;
          bool isg = (ni == ti && nj == tj);
          if ((!forbid[ni][nj] || isg) && dist[np] == -1) {
            dist[np] = dist[cur] + 1;
            prevv[np] = cur;
            act[np] = 'M';
            direc[np] = dirch[d];
            q.push(np);
          }
        }
        // slide
        int ni2 = i;
        int nj2 = j;
        if (d == 0) ni2 = 0;
        else if (d == 1) ni2 = N - 1;
        else if (d == 2) nj2 = 0;
        else nj2 = N - 1;
        if (ni2 != i || nj2 != j) {
          int np2 = ni2 * N + nj2;
          bool isg2 = (ni2 == ti && nj2 == tj);
          if ((!forbid[ni2][nj2] || isg2) && dist[np2] == -1) {
            dist[np2] = dist[cur] + 1;
            prevv[np2] = cur;
            act[np2] = 'S';
            direc[np2] = dirch[d];
            q.push(np2);
          }
        }
      }
    }
    int gpos = ti * N + tj;
    vector<pair<char, char>> path;
    int at = gpos;
    while (at != spos) {
      char ac = act[at];
      char dc = direc[at];
      path.emplace_back(ac, dc);
      at = prevv[at];
    }
    reverse(path.begin(), path.end());
    total.insert(total.end(), path.begin(), path.end());
    current = {ti, tj};
  }
  for (auto [a, d] : total) {
    cout << a << " " << d << '\n';
  }
  return 0;
}