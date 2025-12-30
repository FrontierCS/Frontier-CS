#include <bits/stdc++.h>
using namespace std;

int n;
vector<int> order_;

void ask(int x, int y, int z, vector<pair<int, int>>& res) {
  cout << "? " << x << " " << y << " " << z << endl;
  cout.flush();
  int r;
  cin >> r;
  res.clear();
  for (int i = 0; i < r; i++) {
    int a, b;
    cin >> a >> b;
    if (a > b) swap(a, b);
    res.emplace_back(a, b);
  }
}

int main() {
  int k;
  cin >> k >> n;
  order_.push_back(0);
  if (n == 1) {
    cout << "! 0" << endl;
    cout.flush();
    return 0;
  }
  int first = 1, second = 2;
  vector<pair<int, int>> res;
  ask(0, first, second, res);
  if (n > 2) {
    map<int, int> cnt;
    for (auto p : res) {
      cnt[p.first]++;
      cnt[p.second]++;
    }
    int middle = -1;
    for (auto& pr : cnt) {
      if (pr.second == 2) {
        middle = pr.first;
        break;
      }
    }
    if (middle != -1) {
      vector<int> others;
      vector<int> candidates = {0, first, second};
      for (int d : candidates) {
        if (d != middle) others.push_back(d);
      }
      order_ = {others[0], middle, others[1]};
      // rotate to start with 0 if necessary
      auto it = find(order_.begin(), order_.end(), 0);
      if (it != order_.begin()) {
        rotate(order_.begin(), it, order_.end());
      }
    } else {
      order_ = {0, 1, 2};
    }
  } else {
    order_ = {0, 1};
  }
  for (int y = max(3, 2); y < n; y++) {
    int m = order_.size();
    int low = 0, high = m;
    while (low < high) {
      int mid = low + (high - low) / 2;
      int A = order_[0];
      int B = order_[mid];
      vector<pair<int, int>> qres;
      ask(A, B, y, qres);
      bool only_ab = (qres.size() == 1);
      if (only_ab) {
        int pa = min(A, B), pb = max(A, B);
        only_ab = (qres[0].first == pa && qres[0].second == pb);
      }
      bool between = !only_ab;
      if (between) {
        high = mid;
      } else {
        low = mid + 1;
      }
    }
    order_.insert(order_.begin() + low, y);
  }
  // check direction with first three
  if (n >= 3) {
    vector<pair<int, int>> check_res;
    int a = order_[0], b = order_[1], c = order_[2];
    ask(a, b, c, check_res);
    map<int, int> cnt;
    for (auto p : check_res) {
      cnt[p.first]++;
      cnt[p.second]++;
    }
    int common = -1;
    for (auto& pr : cnt) {
      if (pr.second == 2) {
        common = pr.first;
        break;
      }
    }
    bool good = (common == b);
    if (!good) {
      // reverse the rest
      reverse(order_.begin() + 1, order_.end());
    }
  }
  cout << "!";
  for (int x : order_) {
    cout << " " << x;
  }
  cout << endl;
  cout.flush();
  return 0;
}