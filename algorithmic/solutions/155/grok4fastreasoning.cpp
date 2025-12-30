#include <bits/stdc++.h>
using namespace std;

const char dirs[4] = {'U', 'D', 'L', 'R'};
const int dr[4] = {-1, 1, 0, 0};
const int dc[4] = {0, 0, -1, 1};

bool can_move(int r, int c, int d, const vector<string>& hh, const vector<string>& vv) {
  if (d == 0) { // U
    if (r == 0) return false;
    return vv[r - 1][c] == '0';
  } else if (d == 1) { // D
    if (r == 19) return false;
    return vv[r][c] == '0';
  } else if (d == 2) { // L
    if (c == 0) return false;
    return hh[r][c - 1] == '0';
  } else { // R
    if (c == 19) return false;
    return hh[r][c] == '0';
  }
}

double compute_E(const string& SS, double pp, int stt, int gll, const vector<string>& hh, const vector<string>& vv) {
  int LL = SS.size();
  if (LL == 0) {
    return (stt == gll ? 401.0 : 0.0);
  }
  vector<vector<double>> unreached(LL + 1, vector<double>(400, 0.0));
  unreached[0][stt] = 1.0;
  double exx = 0.0;
  auto is_goal = [gll](int p) { return p == gll; };
  auto get_d = [](char ch) {
    if (ch == 'U') return 0;
    if (ch == 'D') return 1;
    if (ch == 'L') return 2;
    return 3;
  };
  auto cmove = [&](int rr, int cc, int dd) -> pair<int, int> {
    int nnr = rr, nnc = cc;
    if (dd == 0) {
      if (rr > 0 && vv[rr - 1][cc] == '0') nnr = rr - 1;
    } else if (dd == 1) {
      if (rr < 19 && vv[rr][cc] == '0') nnr = rr + 1;
    } else if (dd == 2) {
      if (cc > 0 && hh[rr][cc - 1] == '0') nnc = cc - 1;
    } else {
      if (cc < 19 && hh[rr][cc] == '0') nnc = cc + 1;
    }
    return {nnr, nnc};
  };
  for (int tt = 1; tt <= LL; tt++) {
    int dd = get_d(SS[tt - 1]);
    for (int poss = 0; poss < 400; poss++) {
      double prbb = unreached[tt - 1][poss];
      if (prbb < 1e-12) continue;
      if (is_goal(poss)) continue;
      int rrr = poss / 20, ccc = poss % 20;
      // stay
      unreached[tt][poss] += prbb * pp;
      // move
      auto [nrr, ncc] = cmove(rrr, ccc, dd);
      int nposs = nrr * 20 + ncc;
      double pmove = prbb * (1.0 - pp);
      if (is_goal(nposs)) {
        exx += pmove * (401 - tt);
      } else {
        unreached[tt][nposs] += pmove;
      }
    }
  }
  return exx;
}

int main() {
  int si, sj, ti, tj;
  double p;
  cin >> si >> sj >> ti >> tj >> p;
  vector<string> hh(20);
  for (auto& s : hh) cin >> s;
  vector<string> vv(19);
  for (auto& s : vv) cin >> s;
  int start = si * 20 + sj;
  int goall = ti * 20 + tj;
  vector<int> prevv(400, -1);
  vector<int> moveto(400, -1);
  vector<bool> viss(400, false);
  queue<int> qq;
  qq.push(start);
  viss[start] = true;
  vector<int> dorder = {3, 1, 2, 0}; // R D L U
  while (!qq.empty()) {
    int poss = qq.front(); qq.pop();
    int rrr = poss / 20, ccc = poss % 20;
    for (int dd : dorder) {
      if (can_move(rrr, ccc, dd, hh, vv)) {
        int nrr = rrr + dr[dd];
        int ncc = ccc + dc[dd];
        int nposs = nrr * 20 + ncc;
        if (!viss[nposs]) {
          viss[nposs] = true;
          prevv[nposs] = poss;
          moveto[nposs] = dd;
          qq.push(nposs);
        }
      }
    }
  }
  string basic = "";
  int curr = goall;
  while (curr != start) {
    int dd = moveto[curr];
    basic = dirs[dd] + basic;
    curr = prevv[curr];
  }
  if (basic.empty()) {
    cout << "" << endl;
    return 0;
  }
  int LL = basic.size();
  int maxkk = 200 / LL;
  double beste = -1.0;
  string beststr = "";
  for (int kk = 1; kk <= maxkk; kk++) {
    string cands = "";
    for (int i = 0; i < kk; i++) cands += basic;
    double ee = compute_E(cands, p, start, goall, hh, vv);
    if (ee > beste) {
      beste = ee;
      beststr = cands;
    }
  }
  cout << beststr << endl;
  return 0;
}