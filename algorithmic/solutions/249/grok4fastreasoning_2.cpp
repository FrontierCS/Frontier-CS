#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int n;
  cin >> n;
  vector<int> active[2049];
  for (int i = 1; i <= n; ++i) {
    for (int x = 0; x < n; ++x) {
      active[i].push_back(x);
    }
  }
  int Q = 0;
  const int MAX_Q = 4300;
  while (Q < MAX_Q) {
    // check done
    bool done = true;
    for (int i = 1; i <= n; ++i) {
      if (active[i].size() != 1) {
        done = false;
        break;
      }
    }
    if (done) break;
    // find i1 with max size
    int maxc = -1;
    int i1 = 1;
    for (int i = 1; i <= n; ++i) {
      int c = active[i].size();
      if (c > maxc) {
        maxc = c;
        i1 = i;
      }
    }
    if (maxc == 1) break;
    // find i2 with max inter with i1
    int max_inter = -1;
    int i2 = -1;
    vector<char> has_x(n, 0);
    for (int x : active[i1]) has_x[x] = 1;
    for (int j = 1; j <= n; ++j) {
      if (j == i1) continue;
      int inter = 0;
      for (int x : active[j]) {
        if (has_x[x]) ++inter;
      }
      if (inter > max_inter) {
        max_inter = inter;
        i2 = j;
      }
    }
    if (i2 == -1 || max_inter == 0) {
      // pick largest size
      int maxc2 = -1;
      i2 = 1;
      for (int j = 1; j <= n; ++j) {
        if (j == i1) continue;
        int c = active[j].size();
        if (c > maxc2) {
          maxc2 = c;
          i2 = j;
        }
      }
    }
    if (i1 > i2) swap(i1, i2);
    cout << "? " << i1 << " " << i2 << endl;
    cout.flush();
    int v;
    cin >> v;
    if (v == -1) return 0;
    ++Q;
    // update for i1
    vector<char> good1(n, 0);
    bool skip1 = false;
    for (int aa : active[i1]) {
      if ((aa & ~v) != 0) continue;
      int msk = v & ~aa;
      bool has = false;
      for (int bb : active[i2]) {
        if ((bb & msk) == msk) {
          has = true;
          good1[aa] = 1;  // wait, good1 is for i1, but to set good for i2, need separate
          // actually, to set all good2, I need to loop all
          break; // but to set all good2, I can't break, need full loop for each aa? No, inefficient
    // better to do double loop without break for setting good
    }
    }
    if (has) good1[aa] = 1;
  }
  // wait, the above is incorrect for good2.
  // to fix, do full double loop
  vector<char> good1(n, 0);
  vector<char> good2(n, 0);
  for (int aa : active[i1]) {
    if ((aa & ~v) != 0) continue;
    int msk = v & ~aa;
    bool has = false;
    for (int bb : active[i2]) {
      if ((bb & msk) == msk) {
        has = true;
        good2[bb] = 1;
      }
    }
    if (has) good1[aa] = 1;
  }
  // now for good2 symmetric
  for (int bb : active[i2]) {
    if ((bb & ~v) != 0) continue;
    int msk = v & ~bb;
    bool has = false;
    for (int aa : active[i1]) {
      if ((aa & msk) == msk) {
        has = true;
        good1[aa] = 1;
      }
    }
    if (has) good2[bb] = 1;
  }
  // now new lists
  vector<int> new_active1;
  for (int aa : active[i1]) {
    if (good1[aa]) new_active1.push_back(aa);
  }
  active[i1] = new_active1;
  vector<int> new_active2;
  for (int bb : active[i2]) {
    if (good2[bb]) new_active2.push_back(bb);
  }
  active[i2] = new_active2;
  }
  // extract p
  vector<int> p(n + 1);
  for (int i = 1; i <= n; ++i) {
    assert(active[i].size() == 1);
    p[i] = active[i][0];
  }
  // output
  cout << "!";
  for (int i = 1; i <= n; ++i) {
    cout << " " << p[i];
  }
  cout << endl;
  cout.flush();
  return 0;
}