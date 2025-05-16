# Commit message format
```
<type>[optional scope]: <description>
```

- **feat**: thêm một feature
- **fix**: fix bug cho hệ thống, vá lỗi trong codebase
- **refactor**: sửa code nhưng không fix bug cũng không thêm feature hoặc đôi khi bug cũng được fix từ việc refactor.
- **docs**: thêm/thay đổi document
- **chore**: những sửa đổi nhỏ nhặt không liên quan tới code
- **style**: những thay đổi không làm thay đổi ý nghĩa của code như thay đổi css/ui chẳng hạn.
- **perf**: code cải tiến về mặt hiệu năng xử lý
- **vendor**: cập nhật version cho các dependencies, packages.

# Chia branch làm việc
- Mỗi người sẽ tự tạo một branch riêng từ branch `main` để làm việc, không commit trực tiếp vào branch chính (main).
- Cần tạo pull request để merge branch của mình vào branch chính (main).

