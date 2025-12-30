#include <bits/stdc++.h>
using namespace std;

int n;
vector<pair<int, int>> edges;
set<pair<int, int>> edge_set; // to avoid duplicates

int ask_steiner(int v, const vector<int>& S) {
  int kk = S.size();
  if (kk == 0) return 0;
  cout << "? " << kk << " " << v;
  for (int x : S) cout << " " << x;
  cout << endl;
  cout.flush();
  int res;
  cin >> res;
  if (res == -1) exit(0);
  return res;
}

int ask_path(int v, int a, int b) {
  vector<int> S = {a, b};
  return ask_steiner(v, S);
}

int find_closest(int ll, vector<int> cand) {
  if (cand.empty()) {
    assert(false);
    return -1;
  }
  if (cand.size() == 1) return cand[0];
  vector<int> winners;
  for (size_t i = 0; i < cand.size(); i += 2) {
    if (i + 1 == cand.size()) {
      winners.push_back(cand[i]);
      continue;
    }
    int a = cand[i], b = cand[i + 1];
    int res1 = ask_path(a, ll, b);
    if (res1 == 1) {
      winners.push_back(a);
      continue;
    }
    int res2 = ask_path(b, ll, a);
    if (res2 == 1) {
      winners.push_back(b);
    } else {
      winners.push_back(min(a, b));
    }
  }
  return find_closest(ll, winners);
}

void add_edge(int a, int b) {
  if (a > b) swap(a, b);
  if (edge_set.count({a, b})) return;
  edge_set.insert({a, b});
  edges.emplace_back(a, b);
}

int main() {
  ios::sync_with_stdio(false);
  cin.tie(NULL);
  cin >> n;
  if (n == 1) {
    cout << "!" << endl;
    cout.flush();
    return 0;
  }
  vector<int> currentV(n);
  for (int i = 0; i < n; i++) currentV[i] = i + 1;
  while (true) {
    int sz = currentV.size();
    if (sz <= 2) {
      if (sz == 2) add_edge(currentV[0], currentV[1]);
      break;
    }
    // compute L
    vector<int> L;
    for (int vv : currentV) {
      vector<int> SS;
      for (int x : currentV) if (x != vv) SS.push_back(x);
      int res = ask_steiner(vv, SS);
      if (res == 0) L.push_back(vv);
    }
    sz = currentV.size();
    if (L.size() == sz - 1) {
      // star
      int center = -1;
      for (int vv : currentV) {
        vector<int> SS;
        for (int x : currentV) if (x != vv) SS.push_back(x);
        int res = ask_steiner(vv, SS);
        if (res == 1) {
          center = vv;
          break;
        }
      }
      assert(center != -1);
      for (int ll : L) add_edge(center, ll);
      break;
    }
    if (L.size() == sz - 2) {
      // path of 3 or similar
      vector<int> centers;
      for (int vv : currentV) {
        vector<int> SS;
        for (int x : currentV) if (x != vv) SS.push_back(x);
        int res = ask_steiner(vv, SS);
        if (res == 1) centers.push_back(vv);
      }
      assert(centers.size() == 2);
      int c1 = centers[0], c2 = centers[1];
      add_edge(c1, c2);
      for (int ll : L) {
        int res = ask_path(c1, ll, c2);
        if (res == 1) add_edge(ll, c1);
        else add_edge(ll, c2);
      }
      break;
    }
    // general
    sort(L.begin(), L.end());
    // internals
    vector<int> internals;
    set<int> lset(L.begin(), L.end());
    for (int x : currentV) if (lset.count(x) == 0) internals.push_back(x);
    int fixed_r = internals[0];
    vector<int> pending;
    set<int> this_cand;
    for (size_t ii = 0; ii < L.size(); ii += 10) {
      vector<int> group;
      for (size_t jj = 0; jj < 10 && ii + jj < L.size(); jj++) {
        group.push_back(L[ii + jj]);
      }
      if (group.empty()) break;
      int s = group[0];
      pending.push_back(s);
      for (size_t jj = 1; jj < group.size(); jj++) {
        int ll = group[jj];
        vector<int> P;
        for (int vv : currentV) {
          int res = ask_path(vv, ll, s);
          if (res == 1) P.push_back(vv);
        }
        vector<int> cand;
        for (int pp : P) if (pp != ll) cand.push_back(pp);
        int pp = find_closest(ll, cand);
        add_edge(ll, pp);
        this_cand.insert(pp);
      }
    }
    // process pending
    for (int ll : pending) {
      vector<int> P;
      for (int vv : currentV) {
        int res = ask_path(vv, ll, fixed_r);
        if (res == 1) P.push_back(vv);
      }
      vector<int> cand;
      for (int pp : P) if (pp != ll) cand.push_back(pp);
      int pp = find_closest(ll, cand);
      add_edge(ll, pp);
      this_cand.insert(pp);
    }
    // now remove L
    vector<int> new_current;
    for (int x : currentV) {
      if (lset.count(x) == 0) new_current.push_back(x);
    }
    currentV = new_current;
    // candidates for next
    vector<int> next_cand(this_cand.begin(), this_cand.end());
    // now compute next L from next_cand
    L.clear();
    for (int vv : next_cand) {
      if (find(currentV.begin(), currentV.end(), vv) == currentV.end()) continue;
      vector<int> SS;
      for (int x : currentV) if (x != vv) SS.push_back(x);
      int res = ask_steiner(vv, SS);
      if (res == 0) L.push_back(vv);
    }
  }
  // output
  cout << "!" << endl;
  for (auto [u, v] : edges) {
    cout << u << " " << v << endl;
  }
  cout.flush();
  return 0;
}