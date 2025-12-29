#include <bits/stdc++.h>
using namespace std;

int main() {
  int n, m;
  cin >> n >> m;
  int S = n * m;
  vector<int> a_seq(S);
  // dummy to get initial
  cout << "? 0 1" << endl;
  cout.flush();
  int dummy_a;
  cin >> dummy_a;
  cout << "? 0 -1" << endl;
  cout.flush();
  cin >> a_seq[0];
  // scan
  for (int k = 1; k < S; k++) {
    cout << "? 0 1" << endl;
    cout.flush();
    cin >> a_seq[k];
  }
  // now back to initial
  for (int k = 0; k < S - 1; k++) {
    cout << "? 0 -1" << endl;
    cout.flush();
    int aa;
    cin >> aa;
  }
  int pos0 = -1;
  vector<int> one_U0(S, 0);
  bool found = false;
  for (int ass = 0; ass < S; ass++) {
    vector<int> darr(S);
    for (int k = 0; k < S; k++) {
      int phys = (ass + k) % S;
      darr[phys] = a_seq[(k + 1) % S] - a_seq[k];
    }
    vector<int> ind(S, 0);
    bool val = true;
    for (int res = 0; res < m && val; res++) {
      vector<int> pp(n);
      for (int kk = 0; kk < n; kk++) {
        pp[kk] = (res + 1LL * kk * m) % S;
      }
      // try 0
      vector<int> b0(n);
      b0[0] = 0;
      bool ok0 = true;
      for (int kk = 0; kk < n - 1; kk++) {
        b0[kk + 1] = b0[kk] + darr[pp[kk]];
        if (b0[kk + 1] < 0 || b0[kk + 1] > 1) ok0 = false;
      }
      // try 1
      vector<int> b1(n);
      b1[0] = 1;
      bool ok1 = true;
      for (int kk = 0; kk < n - 1; kk++) {
        b1[kk + 1] = b1[kk] + darr[pp[kk]];
        if (b1[kk + 1] < 0 || b1[kk + 1] > 1) ok1 = false;
      }
      int choose = -1;
      if (ok0 && ok1) {
        bool az = true;
        for (int kk = 0; kk < n - 1; kk++) {
          if (darr[pp[kk]] != 0) az = false;
        }
        if (az) {
          choose = 0;
        } else {
          val = false;
        }
      } else if (ok0) {
        choose = 0;
      } else if (ok1) {
        choose = 1;
      } else {
        val = false;
      }
      if (!val) continue;
      const vector<int>& bb = (choose == 0 ? b0 : b1);
      for (int kk = 0; kk < n; kk++) {
        ind[pp[kk]] = bb[kk];
      }
    }
    if (!val) continue;
    // compute sumu
    int sumu = 0;
    for (int j = 0; j < S; j++) if (ind[j]) sumu++;
    int cst = S - sumu - m;
    // check match
    bool mat = true;
    for (int k = 0; k < S; k++) {
      int dd = (ass + k) % S;
      int ff = 0;
      int temp = dd;
      for (int off = 0; off < m; off++) {
        int jj = temp % S;
        ff += ind[jj];
        temp = (temp + 1);
      }
      int expa = cst + ff;
      if (expa != a_seq[k]) {
        mat = false;
        break;
      }
    }
    if (mat) {
      pos0 = ass;
      one_U0 = ind;
      found = true;
      break;
    }
  }
  assert(found);
  // now find runs
  vector<pair<int, int>> runs;
  int ii = 0;
  while (ii < S) {
    if (one_U0[ii] == 0) {
      ii++;
      continue;
    }
    int st = ii;
    while (ii < S && one_U0[ii]) ii++;
    runs.push_back({st, ii - 1});
  }
  bool is_wrapping = (S > 0 && one_U0[0] && one_U0[S - 1] && !runs.empty() && runs[0].first == 0 && runs.back().second == S - 1);
  if (is_wrapping) {
    int new_st = runs.back().first;
    int new_en = runs[0].second;
    runs.erase(runs.begin());
    if (!runs.empty()) runs.pop_back();
    runs.push_back({new_st, new_en});
  }
  vector<int> cands;
  for (auto& rn : runs) {
    int st = rn.first;
    int en = rn.second;
    int llen;
    bool wrap = (st > en);
    if (!wrap) {
      llen = en - st + 1;
    } else {
      llen = (S - st) + (en + 1);
    }
    if (llen % m != 0) continue;
    int kkk = llen / m;
    long long rstart = st;
    for (int t = 0; t < kkk; t++) {
      long long ps = (rstart + 1LL * t * m) % S;
      cands.push_back(ps);
    }
  }
  sort(cands.begin(), cands.end());
  // now cands has n-1
  assert((int)cands.size() == n - 1);
  // current_a = a_seq[0]
  int current_a = a_seq[0];
  int cur_pos0 = pos0;
  vector<int> pos(n);
  pos[0] = cur_pos0;
  auto in_arc = [&](int j, int p) -> bool {
    long long diff = (j - p + 2LL * S) % S;
    return diff < m;
  };
  for (int ring = 1; ring < n; ring++) {
    // probe +1
    cout << "? " << ring << " 1" << endl;
    cout.flush();
    int ap;
    cin >> ap;
    int dplus = ap - current_a;
    // back
    cout << "? " << ring << " -1" << endl;
    cout.flush();
    int ab;
    cin >> ab;
    // probe -1
    cout << "? " << ring << " -1" << endl;
    cout.flush();
    int am;
    cin >> am;
    int dminu = am - current_a;
    // back
    cout << "? " << ring << " 1" << endl;
    cout.flush();
    int ab2;
    cin >> ab2;
    // find
    int match = -1;
    for (int s : cands) {
      // plus
      bool u_s = in_arc(s, cur_pos0) ? false : true;
      int lm = (s + m) % S;
      bool f_a = !in_arc(lm, cur_pos0) && !one_U0[lm];
      int pp = (u_s ? 1 : 0) - (f_a ? 1 : 0);
      // minus
      int ee = (s + m - 1 + S) % S;
      bool u_e = in_arc(ee, cur_pos0) ? false : true;
      int prr = (s - 1 + S) % S;
      bool f_b = !in_arc(prr, cur_pos0) && !one_U0[prr];
      int pm = (u_e ? 1 : 0) - (f_b ? 1 : 0);
      if (pp == dplus && pm == dminu) {
        match = s;
        break; // assume first or unique
      }
    }
    assert(match != -1);
    pos[ring] = match;
  }
  // output
  cout << "!";
  for (int i = 1; i < n; i++) {
    long long pi = ((long long)pos[i] - pos[0] + S) % S;
    cout << " " << pi;
  }
  cout << endl;
  cout.flush();
  return 0;
}