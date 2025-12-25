#include <bits/stdc++.h>
using namespace std;

long long compute_min_internal(int ci, int cj, const vector<vector<pair<int, int>>>& layers) {
  int rlen = layers.size();
  if (rlen == 0) return 0;
  int n0 = layers[0].size();
  vector<long long> dp(n0);
  for (int p = 0; p < n0; p++) {
    int x = layers[0][p].first, y = layers[0][p].second;
    dp[p] = abs(x - ci) + abs(y - cj);
  }
  vector<long long> curr_dp = dp;
  for (int ll = 1; ll < rlen; ll++) {
    int nprev = layers[ll - 1].size();
    int ncurr = layers[ll].size();
    vector<long long> new_dp(ncurr, LLONG_MAX / 2);
    for (int q = 0; q < ncurr; q++) {
      int x = layers[ll][q].first, y = layers[ll][q].second;
      for (int p = 0; p < nprev; p++) {
        int px = layers[ll - 1][p].first, py = layers[ll - 1][p].second;
        long long d = abs(x - px) + abs(y - py);
        if (curr_dp[p] + d < new_dp[q]) {
          new_dp[q] = curr_dp[p] + d;
        }
      }
    }
    curr_dp = move(new_dp);
  }
  return *min_element(curr_dp.begin(), curr_dp.end());
}

vector<pair<int, int>> get_best_path(int ci, int cj, const vector<vector<pair<int, int>>>& layers) {
  int rlen = layers.size();
  if (rlen == 0) return {};
  int n0 = layers[0].size();
  vector<long long> dp(n0);
  for (int p = 0; p < n0; p++) {
    int x = layers[0][p].first, y = layers[0][p].second;
    dp[p] = abs(x - ci) + abs(y - cj);
  }
  vector<long long> curr_dp = dp;
  vector<vector<int>> pred(rlen);
  for (int ll = 1; ll < rlen; ll++) {
    int nprev = layers[ll - 1].size();
    int ncurr = layers[ll].size();
    vector<long long> new_dp(ncurr, LLONG_MAX / 2);
    vector<int> this_pred(ncurr, -1);
    for (int q = 0; q < ncurr; q++) {
      int x = layers[ll][q].first, y = layers[ll][q].second;
      long long bestq = LLONG_MAX / 2;
      int bestp = -1;
      for (int p = 0; p < nprev; p++) {
        int px = layers[ll - 1][p].first, py = layers[ll - 1][p].second;
        long long d = abs(x - px) + abs(y - py);
        long long cand = curr_dp[p] + d;
        if (cand < bestq) {
          bestq = cand;
          bestp = p;
        }
      }
      new_dp[q] = bestq;
      this_pred[q] = bestp;
    }
    pred[ll] = this_pred;
    curr_dp = move(new_dp);
  }
  // find best last
  int nlast = layers[rlen - 1].size();
  int best_last = 0;
  long long min_cost = curr_dp[0];
  for (int q = 1; q < nlast; q++) {
    if (curr_dp[q] < min_cost) {
      min_cost = curr_dp[q];
      best_last = q;
    }
  }
  // backtrack
  vector<pair<int, int>> path(rlen);
  path[rlen - 1] = layers[rlen - 1][best_last];
  int curr_local = best_last;
  for (int ll = rlen - 1; ll >= 1; ll--) {
    int prev_p = pred[ll][curr_local];
    path[ll - 1] = layers[ll - 1][prev_p];
    curr_local = prev_p;
  }
  return path;
}

int main() {
  int N, M;
  cin >> N >> M;
  int si, sj;
  cin >> si >> sj;
  vector<string> A(N);
  for (int i = 0; i < N; i++) cin >> A[i];
  vector<vector<pair<int, int>>> pos(26);
  for (int i = 0; i < N; i++) {
    for (int j = 0; j < N; j++) {
      int c = A[i][j] - 'A';
      pos[c].emplace_back(i, j);
    }
  }
  set<string> uncovered;
  for (int i = 0; i < M; i++) {
    string t;
    cin >> t;
    uncovered.insert(t);
  }
  string S = "";
  vector<pair<int, int>> sequence;
  int ci = si, cj = sj;
  while (!uncovered.empty() && (int)sequence.size() <= 5000 - 5) {
    string best_t = "";
    long long best_added = LLONG_MAX / 2;
    for (const auto& t : uncovered) {
      long long min_for_t = LLONG_MAX / 2;
      int clen_ = S.size();
      for (int k = 0; k < 5; k++) {
        int rlen_ = 5 - k;
        if (clen_ < k) continue;
        if (k > 0 && S.substr(clen_ - k, k) != t.substr(0, k)) continue;
        vector<vector<pair<int, int>>> layers(rlen_);
        bool val = true;
        for (int ll = 0; ll < rlen_; ll++) {
          int cc = t[k + ll] - 'A';
          layers[ll] = pos[cc];
          if (layers[ll].empty()) {
            val = false;
            break;
          }
        }
        if (!val) continue;
        long long inter = compute_min_internal(ci, cj, layers);
        long long ad = (long long)rlen_ + inter;
        if (ad < min_for_t) min_for_t = ad;
      }
      if (min_for_t < best_added) {
        best_added = min_for_t;
        best_t = t;
      }
    }
    if (best_t.empty()) break;
    // recompute for best_t
    long long min_for_t = LLONG_MAX / 2;
    int chosen_k = -1;
    vector<vector<pair<int, int>>> chosen_layers;
    int clen = S.size();
    string t = best_t;
    for (int k = 0; k < 5; k++) {
      int rlen = 5 - k;
      if (clen < k) continue;
      if (k > 0 && S.substr(clen - k, k) != t.substr(0, k)) continue;
      vector<vector<pair<int, int>>> layers(rlen);
      bool val = true;
      for (int ll = 0; ll < rlen; ll++) {
        int cc = t[k + ll] - 'A';
        layers[ll] = pos[cc];
        if (layers[ll].empty()) val = false;
      }
      if (!val) continue;
      long long inter = compute_min_internal(ci, cj, layers);
      long long ad = (long long)rlen + inter;
      if (ad < min_for_t) {
        min_for_t = ad;
        chosen_k = k;
        chosen_layers = layers;
      }
    }
    auto add_path = get_best_path(ci, cj, chosen_layers);
    int old_len = S.size();
    for (auto p : add_path) {
      sequence.emplace_back(p);
      S += A[p.first][p.second];
      ci = p.first;
      cj = p.second;
    }
    uncovered.erase(best_t);
    // check new
    int start_from = max(0, old_len - 4);
    for (int st = start_from; st <= (int)S.size() - 5; st++) {
      string sub = S.substr(st, 5);
      auto ite = uncovered.find(sub);
      if (ite != uncovered.end()) {
        uncovered.erase(ite);
      }
    }
  }
  for (auto [i, j] : sequence) {
    cout << i << " " << j << '\n';
  }
  return 0;
}