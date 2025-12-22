_gen_proto() {
  python3 -m grpc_tools.protoc -I=./protos --python_out ./terka/$1 --grpc_python_out=./terka/$1 ./protos/${1}.proto
}

task() {
	_gen_proto "task"
}
user() {
	_gen_proto "user"
}
task
