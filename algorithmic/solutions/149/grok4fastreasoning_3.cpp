#include <bits/stdc++.h>
using namespace std;

const int N = 30;
const int P = 60;
double params[P];
double SS[P][P];
double RR[P];
double dist[N][N];
int prevr[N][N];
int prevc[N][N];
int di[4] = {-1, 1, 0, 0};
int dj[4] = {0, 0, -1, 1};

bool solve(double A[P][P + 1], double x[P]) {
  for (int i = 0; i < P; i++) {
    int pivot = i;
    for (int j = i + 1; j < P; j++) {
      if (fabs(A[j][i]) > fabs(A[pivot][i])) pivot = j;
    }
    if (fabs(A[pivot][i]) < 1e-10) return false;
    if (pivot != i) {
      for (int k = 0; k <= P; k++) {
        swap(A[i][k], A[pivot][k]);
      }
    }
    for (int j = i + 1; j < P; j++) {
      double factor = A[j][i] / A[i][i];
      for (int k = i; k <= P; k++) {
        A[j][k] -= factor * A[i][k];
      }
    }
  }
  for (int i = P - 1; i >= 0; i--) {
    double sum = 0;
    for (int j = i + 1; j < P; j++) {
      sum += A[i][j] * x[j];
    }
    x[i] = (A[i][P] - sum) / A[i][i];
  }
  return true;
}

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  memset(SS, 0, sizeof(SS));
  memset(RR, 0, sizeof(RR));
  double lambda = 1e-5;
  for (int i = 0; i < P; i++) {
    params[i] = 1.0;
    SS[i][i] = lambda;
    RR[i] = lambda * 1.0;
  }
  for (int q = 0; q < 1000; q++) {
    int si, sj, ti, tj;
    cin >> si >> sj >> ti >> tj;
    for (int i = 0; i < N; i++)
      for (int j = 0; j < N; j++) dist[i][j] = 1e18;
    memset(prevr, -1, sizeof(prevr));
    memset(prevc, -1, sizeof(prevc));
    using T = tuple<double, int, int>;
    priority_queue<T, vector<T>, greater<T>> pq;
    dist[si][sj] = 0;
    pq.push({0, si, sj});
    while (!pq.empty()) {
      auto [d, x, y] = pq.top();
      pq.pop();
      if (d > dist[x][y]) continue;
      for (int k = 0; k < 4; k++) {
        int nx = x + di[k];
        int ny = y + dj[k];
        if (nx < 0 || nx >= N || ny < 0 || ny >= N) continue;
        double cost = (nx == x) ? params[x] : params[30 + y];
        double nd = d + cost;
        if (nd < dist[nx][ny]) {
          dist[nx][ny] = nd;
          prevr[nx][ny] = x;
          prevc[nx][ny] = y;
          pq.push({nd, nx, ny});
        }
      }
    }
    vector<char> moves;
    int cx = ti, cy = tj;
    while (cx != si || cy != sj) {
      int px = prevr[cx][cy], py = prevc[cx][cy];
      if (px == -1) break;
      int dx = cx - px, dy = cy - py;
      char ch;
      if (dx == -1 && dy == 0)
        ch = 'U';
      else if (dx == 1 && dy == 0)
        ch = 'D';
      else if (dx == 0 && dy == -1)
        ch = 'L';
      else if (dx == 0 && dy == 1)
        ch = 'R';
      else
        ch = '?';
      moves.push_back(ch);
      cx = px;
      cy = py;
    }
    reverse(moves.begin(), moves.end());
    string path = "";
    for (char ch : moves) path += ch;
    cout << path << '\n';
    cout.flush();
    long long cval;
    cin >> cval;
    double c = (double)cval;
    vector<double> counts(P, 0.0);
    int rx = si, ry = sj;
    for (char ch : moves) {
      if (ch == 'U' || ch == 'D') {
        counts[30 + ry] += 1.0;
        if (ch == 'U')
          rx--;
        else
          rx++;
      } else {
        counts[rx] += 1.0;
        if (ch == 'L')
          ry--;
        else
          ry++;
      }
    }
    for (int p = 0; p < P; p++) {
      RR[p] += counts[p] * c;
      for (int qq = 0; qq < P; qq++) {
        SS[p][qq] += counts[p] * counts[qq];
      }
    }
    double tempA[P][P + 1];
    for (int i = 0; i < P; i++) {
      for (int j = 0; j < P; j++) {
        tempA[i][j] = SS[i][j];
      }
      tempA[i][P] = RR[i];
    }
    double newparams[P];
    if (solve(tempA, newparams)) {
      memcpy(params, newparams, sizeof(params));
    }
  }
  return 0;
}