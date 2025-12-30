#include <bits/stdc++.h>
using namespace std;

void perform(vector<int>& arr, int x, int y, int nn) {
  vector<int> temp(nn + 1);
  int idx = 1;
  for (int j = nn - y + 1; j <= nn; ++j) temp[idx++] = arr[j];
  for (int j = x + 1; j <= nn - y; ++j) temp[idx++] = arr[j];
  for (int j = 1; j <= x; ++j) temp[idx++] = arr[j];
  arr = temp;
}

int get_lead(int x, int y, const vector<int>& arr, int nn) {
  int m = nn - x - y;
  int pos = 1;
  int suffix_start = nn - y + 1;
  int suffix_idx = suffix_start;
  int middle_start = x + 1;
  int middle_idx = middle_start;
  int prefix_idx = 1;
  int prefix_offset = y + m;
  while (pos <= nn) {
    int val;
    if (pos <= y) {
      val = arr[suffix_idx++];
    } else if (pos <= y + m) {
      val = arr[middle_idx++];
    } else {
      val = arr[prefix_idx++];
    }
    if (val != pos) return pos - 1;
    ++pos;
  }
  return nn;
}

long long get_id(const vector<int>& perm, int nn, long long n1) {
  long long id = 0;
  long long b = 1;
  for (int j = 1; j <= nn; ++j) {
    id += b * (perm[j] - 1LL);
    b *= n1;
  }
  return id;
}

int main() {
  ios::sync_with_stdio(false);
  cin.tie(nullptr);
  int n;
  cin >> n;
  vector<int> p(n + 1);
  for (int j = 1; j <= n; ++j) cin >> p[j];
  vector<pair<int, int>> ops;
  if (n <= 8) {
    long long n1 = n + 1LL;
    long long maxid = 1;
    for (int j = 0; j < n; ++j) maxid *= n1;
    vector<int> dist(maxid, -1);
    vector<long long> par(maxid, -1);
    vector<pair<int, int>> opused(maxid, {-1, -1});
    long long init_id = get_id(p, n, n1);
    long long target_id = 0;
    if (init_id == target_id) {
      // 0 ops
    } else {
      queue<long long> q;
      q.push(init_id);
      dist[init_id] = 0;
      par[init_id] = -1;
      bool found = false;
      while (!q.empty() && !found) {
        long long cid = q.front();
        q.pop();
        vector<int> perm(n + 1);
        long long temp = cid;
        for (int j = n; j >= 1; --j) {
          perm[j] = (temp % n1) + 1;
          temp /= n1;
        }
        for (int x = 1; x < n && !found; ++x) {
          for (int y = 1; y < n - x && !found; ++y) {
            vector<int> newp = perm;
            perform(newp, x, y, n);
            long long nid = get_id(newp, n, n1);
            if (dist[nid] == -1) {
              dist[nid] = dist[cid] + 1;
              par[nid] = cid;
              opused[nid] = {x, y};
              q.push(nid);
              if (nid == target_id) found = true;
            }
          }
        }
      }
      if (found) {
        vector<pair<int, int>> local_ops;
        long long cur = target_id;
        while (cur != init_id) {
          local_ops.push_back(opused[cur]);
          cur = par[cur];
        }
        reverse(local_ops.begin(), local_ops.end());
        ops = local_ops;
      } else {
        // fallback to greedy
        // but for n<=8, should always find
        assert(false);
      }
    }
  } else {
    // greedy
    vector<int> curr = p;
    int max_tried = min(50, n / 2);
    int stuck_count = 0;
    const int MAX_STUCK = 20;
    while (ops.size() < 4 * n) {
      int lead = 0;
      for (int j = 1; j <= n; ++j) {
        if (curr[j] == j) lead = j;
        else break;
      }
      if (lead == n) break;
      int best_lead = lead;
      pair<int, int> best_xy = {-1, -1};
      // all small x y
      for (int x = 1; x <= max_tried; ++x) {
        for (int y = 1; y <= max_tried; ++y) {
          if (x + y >= n) continue;
          int t = get_lead(x, y, curr, n);
          if (t > best_lead) {
            best_lead = t;
            best_xy = {x, y};
          }
        }
      }
      // special for next
      int nexti = lead + 1;
      int kk = 0;
      for (int j = 1; j <= n; ++j) {
        if (curr[j] == nexti) {
          kk = j;
          break;
        }
      }
      if (kk != 0) {
        // case 1
        int xx = n + kk - nexti;
        if (xx >= kk && xx <= n - 2) {
          int yy = 1;
          if (xx + yy < n) {
            int t = get_lead(xx, yy, curr, n);
            if (t > best_lead) {
              best_lead = t;
              best_xy = {xx, yy};
            }
          }
        }
        // case 2
        int yy = n + nexti - kk;
        if (yy >= n - kk + 1 && yy <= n - 2) {
          int xx = 1;
          if (xx + yy < n) {
            int t = get_lead(xx, yy, curr, n);
            if (t > best_lead) {
              best_lead = t;
              best_xy = {xx, yy};
            }
          }
        }
        // case 3 some y
        for (int yy = 1; yy <= min(30, n - 1); ++yy) {
          int xx = yy + kk - nexti;
          if (xx >= 1 && xx + yy < n && kk >= xx + 1 && kk <= n - yy) {
            int t = get_lead(xx, yy, curr, n);
            if (t > best_lead) {
              best_lead = t;
              best_xy = {xx, yy};
            }
          }
        }
      }
      if (best_lead > lead) {
        int x = best_xy.first;
        int y = best_xy.second;
        ops.emplace_back(x, y);
        perform(curr, x, y, n);
        stuck_count = 0;
      } else {
        stuck_count++;
        int x = 1;
        int y = 1;
        if (n > 2) y = min(2, n - x - 1);
        if (stuck_count > MAX_STUCK) {
          x = n / 2;
          y = 1;
          if (x + y >= n) y = n - x - 1;
          stuck_count = 0;
        }
        ops.emplace_back(x, y);
        perform(curr, x, y, n);
      }
    }
  }
  cout << ops.size() << '\n';
  for (auto [x, y] : ops) {
    cout << x << " " << y << '\n';
  }
  return 0;
}