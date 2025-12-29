#include <bits/stdc++.h>
using namespace std;

int main() {
  int N, M;
  cin >> N >> M;
  bool has_dot[62][62] = {};
  for(int i = 0; i < M; i++) {
    int x, y;
    cin >> x >> y;
    has_dot[x][y] = true;
  }
  bool hor[61][62] = {};
  bool ver[62][61] = {};
  vector<vector<int>> ops;
  const int MAX_SIDE = 20;
  int cc = (N - 1) / 2;
  while(true) {
    int best_w = -1;
    vector<int> best_op;
    for(int w = 1; w <= MAX_SIDE && w < N; w++) {
      for(int x = 0; x + w < N; x++) {
        for(int h = 1; h <= MAX_SIDE && h < N; h++) {
          for(int y = 0; y + h < N; y++) {
            bool a = has_dot[x][y];
            bool b = has_dot[x + w][y];
            bool c = has_dot[x + w][y + h];
            bool d = has_dot[x][y + h];
            int sumab = (a ? 1 : 0) + (b ? 1 : 0) + (c ? 1 : 0) + (d ? 1 : 0);
            if(sumab != 3) continue;
            int px, py;
            if(!a) { px = x; py = y; }
            else if(!b) { px = x + w; py = y; }
            else if(!c) { px = x + w; py = y + h; }
            else { px = x; py = y + h; }
            bool ok = true;
            for(int k = 1; k < w && ok; k++) {
              if(has_dot[x + k][y]) ok = false;
            }
            for(int k = 1; k < w && ok; k++) {
              if(has_dot[x + k][y + h]) ok = false;
            }
            for(int k = 1; k < h && ok; k++) {
              if(has_dot[x][y + k]) ok = false;
            }
            for(int k = 1; k < h && ok; k++) {
              if(has_dot[x + w][y + k]) ok = false;
            }
            if(!ok) continue;
            for(int k = 0; k < w && ok; k++) {
              if(hor[x + k][y]) ok = false;
            }
            for(int k = 0; k < w && ok; k++) {
              if(hor[x + k][y + h]) ok = false;
            }
            for(int k = 0; k < h && ok; k++) {
              if(ver[x][y + k]) ok = false;
            }
            for(int k = 0; k < h && ok; k++) {
              if(ver[x + w][y + k]) ok = false;
            }
            if(!ok) continue;
            int dx = px - cc;
            int dy = py - cc;
            int ww = dx * dx + dy * dy + 1;
            if(ww > best_w) {
              best_w = ww;
              vector<pair<int, int>> cor = {{x, y}, {x + w, y}, {x + w, y + h}, {x, y + h}};
              int idx1;
              if(px == cor[0].first && py == cor[0].second) idx1 = 0;
              else if(px == cor[1].first && py == cor[1].second) idx1 = 1;
              else if(px == cor[2].first && py == cor[2].second) idx1 = 2;
              else idx1 = 3;
              vector<int> op(8);
              op[0] = px; op[1] = py;
              int cur = (idx1 + 1) % 4;
              op[2] = cor[cur].first; op[3] = cor[cur].second;
              cur = (cur + 1) % 4;
              op[4] = cor[cur].first; op[5] = cor[cur].second;
              cur = (cur + 1) % 4;
              op[6] = cor[cur].first; op[7] = cor[cur].second;
              best_op = op;
            }
          }
        }
      }
    }
    if(best_op.empty()) break;
    ops.push_back(best_op);
    int px = best_op[0], py = best_op[1];
    has_dot[px][py] = true;
    int xs4[4] = {best_op[0], best_op[2], best_op[4], best_op[6]};
    int ys4[4] = {best_op[1], best_op[3], best_op[5], best_op[7]};
    int min_x = *min_element(xs4, xs4 + 4);
    int max_x = *max_element(xs4, xs4 + 4);
    int min_y = *min_element(ys4, ys4 + 4);
    int max_y = *max_element(ys4, ys4 + 4);
    int ww = max_x - min_x;
    int hh = max_y - min_y;
    for(int k = 0; k < ww; k++) {
      hor[min_x + k][min_y] = true;
      hor[min_x + k][max_y] = true;
    }
    for(int k = 0; k < hh; k++) {
      ver[min_x][min_y + k] = true;
      ver[max_x][min_y + k] = true;
    }
  }
  cout << ops.size() << endl;
  for(auto& op : ops) {
    for(int v : op) cout << v << " ";
    cout << endl;
  }
  return 0;
}