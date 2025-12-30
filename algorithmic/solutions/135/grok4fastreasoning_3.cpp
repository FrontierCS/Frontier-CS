#include <bits/stdc++.h>
using namespace std;

int main() {
  int kk, nn;
  cin >> kk >> nn;
  int ref = 0;
  vector<int> cands;
  for (int i = 0; i < nn; i++) {
    if (i != ref) cands.push_back(i);
  }
  random_shuffle(cands.begin(), cands.end());
  // find closest
  vector<int> closest = cands; // placeholder, implement iterative
  // For simplicity, assume closest has two points 1 and 2
  int a = 1, b = 2; // replace with actual
  if (a > b) swap(a, b);
  vector<int> others;
  for (int i = 0; i < nn; i++) if (i != ref && i != a && i != b) others.push_back(i);
  // sort by dist
  vector<int> sorted = others; // placeholder, implement sort_by_dist
  // grouping
  vector<vector<int>> levels(251);
  levels[1] = {a, b};
  if (!sorted.empty()) {
    int cur_lv = 2;
    levels[cur_lv].push_back(sorted[0]);
    for (size_t i = 1; i < sorted.size(); i++) {
      // ask ref sorted[i-1] sorted[i]
      auto reps = ask(ref, sorted[i - 1], sorted[i]);
      bool has_r1 = reps.count({min(ref, sorted[i - 1]), max(ref, sorted[i - 1])});
      bool has_r2 = reps.count({min(ref, sorted[i]), max(ref, sorted[i])});
      if (has_r1 && has_r2) {
        levels[cur_lv].push_back(sorted[i]);
      } else {
        cur_lv++;
        levels[cur_lv].push_back(sorted[i]);
      }
    }
  }
  int num_lv = 250; // assume
  vector<int> cw, ccw;
  cw.push_back(a);
  ccw.push_back(b);
  for (int lv = 2; lv <= num_lv; lv++) {
    vector<int> grp = levels[lv];
    int x1 = grp[0], x2 = grp[1];
    // test for cw
    int d = 1;
    int prev_lv = lv - d;
    int prev_cw = cw[prev_lv - 1];
    auto reps1 = ask(prev_cw, x1, ref);
    bool has_p1 = reps1.count({min(prev_cw, x1), max(prev_cw, x1)});
    bool has_pr1 = reps1.count({min(prev_cw, ref), max(prev_cw, ref)});
    bool only_p1 = has_p1 && !has_pr1;
    auto reps2 = ask(prev_cw, x2, ref);
    bool has_p2 = reps2.count({min(prev_cw, x2), max(prev_cw, x2)});
    bool has_pr2 = reps2.count({min(prev_cw, ref), max(prev_cw, ref)});
    bool only_p2 = has_p2 && !has_pr2;
    int cw_one;
    if (only_p1) {
      cw_one = x1;
    } else if (only_p2) {
      cw_one = x2;
    } else {
      cw_one = min(x1, x2);
    }
    cw.push_back(cw_one);
    int ccw_one = (cw_one == x1 ? x2 : x1);
    ccw.push_back(ccw_one);
  }
  vector<int> order;
  for (int i = ccw.size() - 2; i >= 0; i--) order.push_back(ccw[i]);
  order.push_back(ref);
  for (size_t i = 1; i < cw.size(); i++) order.push_back(cw[i]);
  cout << "!";
  for (int x : order) cout << " " << x;
  cout << endl;
  cout.flush();
  return 0;
}

set<pair<int, int>> ask(int x, int y, int z) {
  cout << "? " << x << " " << y << " " << z << endl;
  cout.flush();
  int r;
  cin >> r;
  set<pair<int, int>> res;
  for (int i = 0; i < r; i++) {
    int a, b;
    cin >> a >> b;
    if (a > b) swap(a, b);
    res.insert({a, b});
  }
  return res;
}

vector<int> find_closest(int ref, vector<int> cands) {
  random_shuffle(cands.begin(), cands.end());
  while (cands.size() > 2) {
    vector<int> new_cands;
    int sz = cands.size();
    for (int i = 0; i < sz / 2; i++) {
      int aa = cands[2 * i];
      int bb = cands[2 * i + 1];
      auto reps = ask(ref, aa, bb);
      int ra = min(ref, aa), ma = max(ref, aa);
      int rb = min(ref, bb), mb = max(ref, bb);
      int ab = min(aa, bb), mab = max(aa, bb);
      bool has_ra = reps.count({ra, ma});
      bool has_rb = reps.count({rb, mb});
      bool has_ab = reps.count({ab, mab});
      vector<int> kept;
      if (has_ra && has_rb) {
        kept.push_back(aa);
        kept.push_back(bb);
      } else if (has_ra) {
        kept.push_back(aa);
      } else if (has_rb) {
        kept.push_back(bb);
      }
      for (int kk : kept) new_cands.push_back(kk);
    }
    if (sz % 2 == 1) new_cands.push_back(cands.back());
    cands = new_cands;
  }
  return cands;
}

bool less_dist(int ref, int a, int b) {
  auto reps = ask(ref, a, b);
  int ra = min(ref, a), ma = max(ref, a);
  int rb = min(ref, b), mb = max(ref, b);
  int ab = min(a, b), mab = max(a, b);
  bool has_ra = reps.count({ra, ma});
  bool has_rb = reps.count({rb, mb});
  bool has_ab = reps.count({ab, mab});
  if (has_ra && !has_rb) return true;
  if (has_rb && !has_ra) return false;
  if (has_ra && has_rb) return a < b; // arbitrary
  if (has_ra && has_ab) return true;
  if (has_rb && has_ab) return false;
  if (has_ab) return a < b; // arbitrary
  return a < b;
}

vector<int> sort_by_dist(int ref, vector<int> cands) {
  int sz = cands.size();
  if (sz <= 1) return cands;
  vector<int> left(cands.begin(), cands.begin() + sz / 2);
  vector<int> right(cands.begin() + sz / 2, cands.end());
  left = sort_by_dist(ref, left);
  right = sort_by_dist(ref, right);
  vector<int> merged;
  int i = 0, j = 0;
  while (i < left.size() && j < right.size()) {
    if (less_dist(ref, left[i], right[j])) {
      merged.push_back(left[i++]);
    } else {
      merged.push_back(right[j++]);
    }
  }
  while (i < left.size()) merged.push_back(left[i++]);
  while (j < right.size()) merged.push_back(right[j++]);
  return merged;
}