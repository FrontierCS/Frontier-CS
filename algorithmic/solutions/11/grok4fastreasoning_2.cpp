#include <bits/stdc++.h>
using namespace std;

int n, m, sr, sc, er, ec;
string grid[30];
bool vis[30][30];
int par_i[30][30], par_j[30][30], par_dir[30][30];
vector<pair<pair<int, int>, int>> child_list[30][30];
int di[4] = {-1, 0, 1, 0};
int dj[4] = {0, 1, 0, -1};
char dirc[4] = {'U', 'R', 'D', 'L'};

void build_tree(int i, int j, const vector<int>& order) {
  vis[i][j] = true;
  for (int k : order) {
    int d = k;
    int ni = i + di[d];
    int nj = j + dj[d];
    if (ni >= 0 && ni < n && nj >= 0 && nj < m && grid[ni][nj] == '1' && !vis[ni][nj]) {
      par_i[ni][nj] = i;
      par_j[ni][nj] = j;
      par_dir[ni][nj] = d;
      child_list[i][j].emplace_back(make_pair(ni, nj), d);
      build_tree(ni, nj, order);
    }
  }
}

string full_traverse(int i, int j) {
  string res = "";
  for (auto& ch : child_list[i][j]) {
    int d = ch.second;
    pair<int, int> p = ch.first;
    int ni = p.first, nj = p.second;
    res += dirc[d];
    res += full_traverse(ni, nj);
    res += dirc[(d + 2) % 4];
  }
  return res;
}

string generate_B(int si, int sj, int ti, int tj) {
  vector<pair<int, int>> path;
  int ci = ti, cj = tj;
  while (ci != si || cj != sj) {
    path.emplace_back(ci, cj);
    int pi = par_i[ci][cj], pj = par_j[ci][cj];
    if (pi == -1) return "";
    ci = pi;
    cj = pj;
  }
  path.emplace_back(si, sj);
  reverse(path.begin(), path.end());
  string res = "";
  size_t L = path.size();
  for (size_t k = 0; k < L - 1; ++k) {
    int i = path[k].first, j = path[k].second;
    pair<int, int> next_pos = {path[k + 1].first, path[k + 1].second};
    for (auto& ch : child_list[i][j]) {
      if (ch.first != next_pos) {
        int d = ch.second;
        auto p = ch.first;
        int ni = p.first, nj = p.second;
        res += dirc[d];
        res += full_traverse(ni, nj);
        res += dirc[(d + 2) % 4];
      }
    }
    int ni = next_pos.first, nj = next_pos.second;
    int d = par_dir[ni][nj];
    res += dirc[d];
  }
  int i = path.back().first, j = path.back().second;
  for (auto& ch : child_list[i][j]) {
    int d = ch.second;
    auto p = ch.first;
    int ni = p.first, nj = p.second;
    res += dirc[d];
    res += full_traverse(ni, nj);
    res += dirc[(d + 2) % 4];
  }
  return res;
}

pair<int, int> simulate(const string& seq, int si, int sj, set<pair<int, int>>& visited) {
  int ci = si, cj = sj;
  visited.insert({ci, cj});
  for (char ch : seq) {
    int d = -1;
    if (ch == 'U') d = 0;
    if (ch == 'R') d = 1;
    if (ch == 'D') d = 2;
    if (ch == 'L') d = 3;
    int ni = ci + di[d];
    int nj = cj + dj[d];
    if (ni >= 0 && ni < n && nj >= 0 && nj < m && grid[ni][nj] == '1') {
      ci = ni;
      cj = nj;
    }
    visited.insert({ci, cj});
  }
  return {ci, cj};
}

int main() {
  cin >> n >> m;
  for (int i = 0; i < n; i++) cin >> grid[i];
  cin >> sr >> sc >> er >> ec;
  sr--;
  sc--;
  er--;
  ec--;
  int K = 0;
  for (int i = 0; i < n; i++)
    for (int j = 0; j < m; j++)
      if (grid[i][j] == '1') K++;
  bool vis_conn[30][30] = {0};
  queue<pair<int, int>> q;
  q.push({sr, sc});
  vis_conn[sr][sc] = true;
  int reached = 1;
  while (!q.empty()) {
    auto [i, j] = q.front();
    q.pop();
    for (int d = 0; d < 4; d++) {
      int ni = i + di[d], nj = j + dj[d];
      if (ni >= 0 && ni < n && nj >= 0 && nj < m && grid[ni][nj] == '1' && !vis_conn[ni][nj]) {
        vis_conn[ni][nj] = true;
        reached++;
        q.push({ni, nj});
      }
    }
  }
  if (reached != K) {
    cout << -1 << endl;
    return 0;
  }
  vector<int> order(4);
  iota(order.begin(), order.end(), 0);
  string ans = "-1";
  do {
    for (int x = 0; x < n; x++)
      for (int y = 0; y < m; y++) {
        child_list[x][y].clear();
        par_i[x][y] = -1;
        par_j[x][y] = -1;
        par_dir[x][y] = -1;
        vis[x][y] = false;
      }
    build_tree(sr, sc, order);
    string B = generate_B(sr, sc, er, ec);
    string revB = B;
    reverse(revB.begin(), revB.end());
    string S = revB + B;
    set<pair<int, int>> visited;
    auto [fi, fj] = simulate(S, sr, sc, visited);
    if (fi == er && fj == ec && (int)visited.size() == K) {
      ans = S;
      break;
    }
  } while (next_permutation(order.begin(), order.end()));
  if (ans == "-1") {
    cout << -1 << endl;
  } else if (ans.empty()) {
    cout << endl;
  } else {
    cout << ans << endl;
  }
  return 0;
}