#include <iostream>
#include <vector>

using namespace std;

int main() {
    int N = 49, M = 49;
    vector<vector<char>> grid(N, vector<char>(M, '#'));
    
    int r = 1, c = 1;
    int dir = 0;
    int step_len = 1;
    int steps = 0;
    int turn_counter = 0;
    int max_steps = N * M;
    int count = 0;
    
    while (count < max_steps) {
        if (dir == 0 || dir == 2) {
            if (r >= 0 && r < N && c >= 0 && c < M && r + 1 < N) {
                grid[r][c] = '.';
                grid[r + 1][c] = '.';
            } else {
                break;
            }
        } else {
            if (r >= 0 && r < N && c >= 0 && c < M && c + 1 < M) {
                grid[r][c] = '.';
                grid[r][c + 1] = '.';
            } else {
                break;
            }
        }
        
        int nr = r, nc = c;
        if (dir == 0) nc++;
        else if (dir == 1) nr++;
        else if (dir == 2) nc--;
        else nr--;
        
        steps++;
        if (steps == step_len) {
            steps = 0;
            dir = (dir + 1) % 4;
            turn_counter++;
            if (turn_counter % 2 == 0) {
                step_len++;
            }
        }
        r = nr;
        c = nc;
        count++;
    }
    
    grid[1][1] = 'B';
    grid[2][1] = 'B';
    grid[1][2] = 'B';
    grid[2][2] = 'B';
    
    int sr = N / 2, sc = M / 2;
    grid[sr - 1][sc - 1] = 'S';
    grid[sr - 1][sc] = 'S';
    grid[sr][sc - 1] = 'S';
    grid[sr][sc] = 'S';
    
    if (grid[1][3] == '.') {
        grid[1][3] = 'P';
    } else if (grid[1][0] == '.') {
        grid[1][0] = 'P';
    } else if (grid[0][1] == '.') {
        grid[0][1] = 'P';
    } else if (grid[3][1] == '.') {
        grid[3][1] = 'P';
    } else {
        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < M; ++j) {
                if (grid[i][j] == '.') {
                    grid[i][j] = 'P';
                    goto done;
                }
            }
        }
    }
done:
    
    cout << N << " " << M << endl;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < M; ++j) {
            cout << grid[i][j];
        }
        cout << endl;
    }
    
    return 0;
}